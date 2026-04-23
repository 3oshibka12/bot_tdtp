package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"time"
)

type TestCase struct {
	Broker      string
	MessageSize int
	Rate        int
	Duration    time.Duration
}

type Result struct {
	TestCase
	Sent       int64
	Received   int64
	Errors     int64
	Throughput float64
	AvgLatency time.Duration
	P95Latency time.Duration
}

func main() {
	brokers := []string{"rabbitmq", "redis"}
	sizes := []int{128, 1024, 10240, 102400} // 128B, 1KB, 10KB, 100KB
	rates := []int{1000, 5000, 10000}
	duration := 30 * time.Second

	var results []Result

	for _, broker := range brokers {
		for _, size := range sizes {
			for _, rate := range rates {
				log.Printf("\n=== Running test: broker=%s, size=%d, rate=%d ===\n", broker, size, rate)

				tc := TestCase{
					Broker:      broker,
					MessageSize: size,
					Rate:        rate,
					Duration:    duration,
				}

				result := runTest(tc)
				results = append(results, result)

				// Пауза между тестами
				time.Sleep(5 * time.Second)
			}
		}
	}

	// Сохраняем результаты
	saveResults(results)
	printSummary(results)
}

func runTest(tc TestCase) Result {
	// Запускаем consumer
	consumerCmd := exec.Command("go", "run", "cmd/consumer/main.go",
		"-broker", tc.Broker,
		"-duration", tc.Duration.String(),
	)
	consumerCmd.Stdout = os.Stdout
	consumerCmd.Stderr = os.Stderr
	consumerCmd.Start()

	// Даём consumer время на запуск
	time.Sleep(2 * time.Second)

	// Запускаем producer
	producerCmd := exec.Command("go", "run", "cmd/producer/main.go",
		"-broker", tc.Broker,
		"-size", strconv.Itoa(tc.MessageSize),
		"-rate", strconv.Itoa(tc.Rate),
		"-duration", tc.Duration.String(),
	)
	producerCmd.Stdout = os.Stdout
	producerCmd.Stderr = os.Stderr
	producerCmd.Run()

	// Ждём завершения consumer
	consumerCmd.Wait()

	// TODO: парсить вывод и собирать метрики
	// Для простоты возвращаем заглушку
	return Result{
		TestCase:   tc,
		Sent:       int64(tc.Rate) * int64(tc.Duration.Seconds()),
		Received:   int64(tc.Rate) * int64(tc.Duration.Seconds()),
		Throughput: float64(tc.Rate),
	}
}

func saveResults(results []Result) {
	f, err := os.Create("results/benchmark_results.csv")
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	defer w.Flush()

	// Header
	w.Write([]string{"Broker", "MessageSize", "Rate", "Sent", "Received", "Errors", "Throughput", "AvgLatency", "P95Latency"})

	for _, r := range results {
		w.Write([]string{
			r.Broker,
			strconv.Itoa(r.MessageSize),
			strconv.Itoa(r.Rate),
			strconv.FormatInt(r.Sent, 10),
			strconv.FormatInt(r.Received, 10),
			strconv.FormatInt(r.Errors, 10),
			fmt.Sprintf("%.2f", r.Throughput),
			r.AvgLatency.String(),
			r.P95Latency.String(),
		})
	}

	log.Println("✅ Results saved to results/benchmark_results.csv")
}

func printSummary(results []Result) {
	fmt.Println("\n=== SUMMARY ===")
	for _, r := range results {
		fmt.Printf("%s | size=%d | rate=%d | throughput=%.2f msg/sec\n",
			r.Broker, r.MessageSize, r.Rate, r.Throughput)
	}
}