package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"benchmark/internal/metrics"
)

type TestCase struct {
	Broker      string
	MessageSize int
	Rate        int
	Duration    time.Duration
	QueueName   string
}

type Result struct {
	TestCase
	Sent         int64
	Received     int64
	Errors       int64
	Throughput   float64
	AvgLatencyMs float64
	P95LatencyMs float64
}

func main() {
	// Сначала компилируем бинарники, чтобы не тратить время в тестах
	buildBinaries()

	brokers := []string{"redis", "rabbitmq"}
	sizes := []int{128, 1024, 10240}
	rates := []int{1000, 5000}
	duration := 10 * time.Second

	var testCases []TestCase
	for _, broker := range brokers {
		for _, size := range sizes {
			for _, rate := range rates {
				testCases = append(testCases, TestCase{
					Broker:      broker,
					MessageSize: size,
					Rate:        rate,
					Duration:    duration,
					QueueName:   fmt.Sprintf("bench_%s", broker),
				})
			}
		}
	}

	log.Printf("🚀 Starting %d tests sequentially...\n", len(testCases))

	var results []Result
	for _, tc := range testCases {
		log.Printf("▶️  Test: %s | Size: %d | Rate: %d", tc.Broker, tc.MessageSize, tc.Rate)
		res := runTest(tc)
		results = append(results, res)
		log.Printf("✅ Done: %.0f msg/sec", res.Throughput)
		// Небольшая пауза между тестами для очистки памяти брокеров
		time.Sleep(2 * time.Second)
	}

	saveResults(results)
	printSummary(results)
}

func buildBinaries() {
	log.Println("🔨 Compiling binaries...")
	os.MkdirAll("bin", 0755)
	
	cmd1 := exec.Command("go", "build", "-o", "bin/consumer", "./cmd/consumer/main.go")
	if err := cmd1.Run(); err != nil {
		log.Fatalf("Failed to build consumer: %v", err)
	}
	
	cmd2 := exec.Command("go", "build", "-o", "bin/producer", "./cmd/producer/main.go")
	if err := cmd2.Run(); err != nil {
		log.Fatalf("Failed to build producer: %v", err)
	}
}

func runTest(tc TestCase) Result {
	ctx, cancel := context.WithTimeout(context.Background(), tc.Duration+10*time.Second)
	defer cancel()

	consOut := filepath.Join(os.TempDir(), fmt.Sprintf("cons_%d.json", time.Now().UnixNano()))
	prodOut := filepath.Join(os.TempDir(), fmt.Sprintf("prod_%d.json", time.Now().UnixNano()))
	defer os.Remove(consOut)
	defer os.Remove(prodOut)

	// Запускаем Consumer
	consumerCmd := exec.CommandContext(ctx, "./bin/consumer",
		"-broker", tc.Broker,
		"-duration", tc.Duration.String(),
		"-queue", tc.QueueName,
		"-output", consOut,
	)
	if err := consumerCmd.Start(); err != nil {
		log.Printf("Consumer start error: %v", err)
	}

	time.Sleep(2 * time.Second) // Даем время подключиться

	// Запускаем Producer
	producerCmd := exec.CommandContext(ctx, "./bin/producer",
		"-broker", tc.Broker,
		"-size", strconv.Itoa(tc.MessageSize),
		"-rate", strconv.Itoa(tc.Rate),
		"-duration", tc.Duration.String(),
		"-queue", tc.QueueName,
		"-output", prodOut,
	)
	
	if out, err := producerCmd.CombinedOutput(); err != nil {
		log.Printf("Producer error: %v, output: %s", err, string(out))
	}

	// Ждем завершения consumer
	consumerCmd.Wait()

	cStats := readStats(consOut)
	pStats := readStats(prodOut)

	return Result{
		TestCase:     tc,
		Sent:         pStats.Sent,
		Received:     cStats.Received,
		Errors:       pStats.Errors + cStats.Errors,
		Throughput:   cStats.Throughput(),
		AvgLatencyMs: cStats.AvgLatencyMs,
		P95LatencyMs: cStats.P95LatencyMs,
	}
}

func readStats(filename string) metrics.Stats {
	data, err := os.ReadFile(filename)
	if err != nil {
		return metrics.Stats{}
	}
	var s metrics.Stats
	json.Unmarshal(data, &s)
	return s
}

func saveResults(results []Result) {
	os.MkdirAll("results", 0755)
	f, _ := os.Create("results/benchmark_results.csv")
	defer f.Close()
	w := csv.NewWriter(f)
	defer w.Flush()

	w.Write([]string{"Broker", "Size", "Rate", "Sent", "Received", "Throughput", "AvgLat", "P95Lat"})
	for _, r := range results {
		w.Write([]string{
			r.Broker, strconv.Itoa(r.MessageSize), strconv.Itoa(r.Rate),
			strconv.FormatInt(r.Sent, 10), strconv.FormatInt(r.Received, 10),
			fmt.Sprintf("%.2f", r.Throughput), fmt.Sprintf("%.2f", r.AvgLatencyMs), fmt.Sprintf("%.2f", r.P95LatencyMs),
		})
	}
}

func printSummary(results []Result) {
	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Printf("%-10s | %-6s | %-6s | %-10s | %-8s\n", "Broker", "Size", "Rate", "T-put", "Avg Lat")
	fmt.Println(strings.Repeat("-", 60))
	for _, r := range results {
		fmt.Printf("%-10s | %-6d | %-6d | %-10.1f | %-8.2fms\n",
			r.Broker, r.MessageSize, r.Rate, r.Throughput, r.AvgLatencyMs)
	}
}