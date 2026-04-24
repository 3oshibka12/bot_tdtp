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
)

func main() {
	brokerType := flag.String("broker", "rabbitmq", "Broker type")
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
		log.Printf("🔄 Consumer: broker=%s, duration=%s", b.Name(), *duration)
	}

	m := metrics.New()
	ctx, cancel := context.WithTimeout(context.Background(), *duration)
	defer cancel()

	msgChan, errChan := b.Consume(ctx)

	for {
		select {
		case <-ctx.Done():
			m.Finalize()
			stats := m.GetStats()

			if *outputFile != "" {
				saveStats(*outputFile, stats)
			} else {
				printStats(stats, b.Name())
			}
			return

		case msg, ok := <-msgChan:
			if !ok {
				return
			}
			latency := time.Since(msg.Timestamp)
			m.IncrementReceived(latency)

		case err := <-errChan:
			if err != nil {
				m.IncrementErrors()
			}
		}
	}
}

func saveStats(filename string, s metrics.Stats) {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(filename, data, 0644)
}

func printStats(s metrics.Stats, brokerName string) {
	fmt.Println("\n=== CONSUMER RESULTS ===")
	fmt.Printf("Broker:       %s\n", brokerName)
	fmt.Printf("Received:     %d\n", s.Received)
	fmt.Printf("Errors:       %d\n", s.Errors)
	fmt.Printf("Duration:     %s\n", s.Duration)
	fmt.Printf("Throughput:   %.2f msg/sec\n", s.Throughput())
	fmt.Printf("Avg latency:  %.2f ms\n", s.AvgLatencyMs)
	fmt.Printf("P95 latency:  %.2f ms\n", s.P95LatencyMs)
	fmt.Printf("Max latency:  %.2f ms\n", s.MaxLatencyMs)
}