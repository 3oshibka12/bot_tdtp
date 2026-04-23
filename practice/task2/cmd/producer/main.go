package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"time"

	"benchmark/internal/broker"
	"benchmark/internal/config"
	"benchmark/internal/metrics"

	"github.com/google/uuid"
)

func main() {
	brokerType := flag.String("broker", "rabbitmq", "Broker type: rabbitmq or redis")
	messageSize := flag.Int("size", 128, "Message size in bytes")
	rate := flag.Int("rate", 1000, "Messages per second")
	duration := flag.Duration("duration", 30*time.Second, "Test duration")
	flag.Parse()

	cfg := config.Default()
	cfg.BrokerType = *brokerType

	// Создаём брокер
	var b broker.Broker
	var err error

	if *brokerType == "rabbitmq" {
		b, err = broker.NewRabbitMQ(cfg.RabbitMQURL, cfg.QueueName)
	} else {
		b, err = broker.NewRedis(cfg.RedisAddr, cfg.QueueName)
	}

	if err != nil {
		log.Fatalf("Failed to create broker: %v", err)
	}
	defer b.Close()

	log.Printf("🚀 Starting producer: broker=%s, size=%d bytes, rate=%d msg/sec, duration=%s",
		b.Name(), *messageSize, *rate, *duration)

	m := metrics.New()
	ctx, cancel := context.WithTimeout(context.Background(), *duration)
	defer cancel()

	// Генерируем payload
	payload := make([]byte, *messageSize)
	for i := range payload {
		payload[i] = byte(i % 256)
	}

	// Throttling
	ticker := time.NewTicker(time.Second / time.Duration(*rate))
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			m.Finalize()
			stats := m.GetStats()
			printStats(stats, b.Name(), *messageSize, *rate)
			return

		case <-ticker.C:
			msg := broker.Message{
				ID:        uuid.New().String(),
				Payload:   payload,
				Timestamp: time.Now(),
			}

			if err := b.Publish(ctx, msg); err != nil {
				m.IncrementErrors()
				log.Printf("Publish error: %v", err)
			} else {
				m.IncrementSent()
			}
		}
	}
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