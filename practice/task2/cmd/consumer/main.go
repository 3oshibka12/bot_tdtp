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
)

func main() {
	brokerType := flag.String("broker", "rabbitmq", "Broker type: rabbitmq or redis")
	duration := flag.Duration("duration", 30*time.Second, "Test duration")
	flag.Parse()

	cfg := config.Default()
	cfg.BrokerType = *brokerType

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

	log.Printf("🔄 Starting consumer: broker=%s, duration=%s", b.Name(), *duration)

	m := metrics.New()
	ctx, cancel := context.WithTimeout(context.Background(), *duration)
	defer cancel()

	msgChan, errChan := b.Consume(ctx)

	for {
		select {
		case <-ctx.Done():
			m.Finalize()
			stats := m.GetStats()
			printStats(stats, b.Name())
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
				log.Printf("Consume error: %v", err)
			}
		}
	}
}

func printStats(s metrics.Stats, brokerName string) {
	fmt.Println("\n=== CONSUMER RESULTS ===")
	fmt.Printf("Broker:       %s\n", brokerName)
	fmt.Printf("Received:     %d\n", s.Received)
	fmt.Printf("Errors:       %d\n", s.Errors)
	fmt.Printf("Duration:     %s\n", s.Duration)
	fmt.Printf("Throughput:   %.2f msg/sec\n", s.Throughput())
	fmt.Printf("Avg latency:  %s\n", s.AvgLatency)
	fmt.Printf("P95 latency:  %s\n", s.P95Latency)
	fmt.Printf("Max latency:  %s\n", s.MaxLatency)
}