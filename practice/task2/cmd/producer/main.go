package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"benchmark/internal/broker"
	"benchmark/internal/config"
	"benchmark/internal/metrics"

	"github.com/google/uuid"
)

func main() {
	brokerType := flag.String("broker", "rabbitmq", "Broker type")
	messageSize := flag.Int("size", 128, "Message size in bytes")
	rate := flag.Int("rate", 1000, "Messages per second")
	duration := flag.Duration("duration", 30*time.Second, "Test duration")
	queueName := flag.String("queue", "benchmark_queue", "Queue name")
	outputFile := flag.String("output", "", "Output JSON file")
	flag.Parse()

	cfg := config.Default()
	cfg.BrokerType = *brokerType

	var b broker.Broker
	var err error

	if *brokerType == "rabbitmq" {
		b, err = broker.NewRabbitMQ(cfg.RabbitMQURL, *queueName)
	} else {
		b, err = broker.NewRedis(cfg.RedisAddr, *queueName)
	}

	if err != nil {
		log.Fatalf("Failed to create broker: %v", err)
	}
	defer b.Close()

	if *outputFile == "" {
		log.Printf("🚀 Producer: broker=%s, size=%d, rate=%d, duration=%s",
			b.Name(), *messageSize, *rate, *duration)
	}

	m := metrics.New()
	ctx, cancel := context.WithTimeout(context.Background(), *duration)
	defer cancel()

	payload := make([]byte, *messageSize)
	for i := range payload {
		payload[i] = byte(i % 256)
	}

	ticker := time.NewTicker(time.Second / time.Duration(*rate))
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			m.Finalize()
			stats := m.GetStats()

			if *outputFile != "" {
				saveStats(*outputFile, stats)
			} else {
				printStats(stats, b.Name(), *messageSize, *rate)
			}
			return

		case <-ticker.C:
			msg := broker.Message{
				ID:        uuid.New().String(),
				Payload:   payload,
				Timestamp: time.Now(),
			}

			if err := b.Publish(ctx, msg); err != nil {
				m.IncrementErrors()
			} else {
				m.IncrementSent()
			}
		}
	}
}

func saveStats(filename string, s metrics.Stats) {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(filename, data, 0644)
}

func printStats(s metrics.Stats, brokerName string, size, rate int) {
	fmt.Println("\n=== PRODUCER RESULTS ===")
	fmt.Printf("Broker:       %s\n", brokerName)
	fmt.Printf("Message size: %d bytes\n", size)
	fmt.Printf("Target rate:  %d msg/sec\n", rate)
	fmt.Printf("Sent:         %d\n", s.Sent)
	fmt.Printf("Errors:       %d\n", s.Errors)
	fmt.Printf("Duration:     %s\n", s.Duration)
	fmt.Printf("Actual rate:  %.2f msg/sec\n", s.Throughput())
}