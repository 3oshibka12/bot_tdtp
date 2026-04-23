package metrics

import (
	"sync"
	"time"
)

type Metrics struct {
	mu sync.Mutex

	Sent      int64
	Received  int64
	Errors    int64
	Latencies []time.Duration
	StartTime time.Time
	EndTime   time.Time
}

func New() *Metrics {
	return &Metrics{
		Latencies: make([]time.Duration, 0, 10000),
		StartTime: time.Now(),
	}
}

func (m *Metrics) IncrementSent() {
	m.mu.Lock()
	m.Sent++
	m.mu.Unlock()
}

func (m *Metrics) IncrementReceived(latency time.Duration) {
	m.mu.Lock()
	m.Received++
	m.Latencies = append(m.Latencies, latency)
	m.mu.Unlock()
}

func (m *Metrics) IncrementErrors() {
	m.mu.Lock()
	m.Errors++
	m.mu.Unlock()
}

func (m *Metrics) Finalize() {
	m.mu.Lock()
	if m.EndTime.IsZero() {
		m.EndTime = time.Now()
	}
	m.mu.Unlock()
}

func (m *Metrics) GetStats() Stats {
	m.mu.Lock()
	defer m.mu.Unlock()

	duration := m.EndTime.Sub(m.StartTime)
	if duration == 0 {
		duration = time.Since(m.StartTime)
	}

	if len(m.Latencies) == 0 {
		return Stats{
			Sent:     m.Sent,
			Received: m.Received,
			Errors:   m.Errors,
			Duration: duration,
		}
	}

	// Копируем и сортируем
	latencies := make([]time.Duration, len(m.Latencies))
	copy(latencies, m.Latencies)
	sortDurations(latencies)

	var total time.Duration
	for _, l := range latencies {
		total += l
	}

	p95Index := int(float64(len(latencies)) * 0.95)
	if p95Index >= len(latencies) {
		p95Index = len(latencies) - 1
	}

	return Stats{
		Sent:       m.Sent,
		Received:   m.Received,
		Errors:     m.Errors,
		AvgLatency: total / time.Duration(len(latencies)),
		P95Latency: latencies[p95Index],
		MaxLatency: latencies[len(latencies)-1],
		Duration:   duration,
	}
}

type Stats struct {
	Sent       int64
	Received   int64
	Errors     int64
	AvgLatency time.Duration
	P95Latency time.Duration
	MaxLatency time.Duration
	Duration   time.Duration
}

func (s Stats) Throughput() float64 {
	if s.Duration.Seconds() == 0 {
		return 0
	}
	return float64(s.Received) / s.Duration.Seconds()
}

func sortDurations(arr []time.Duration) {
	n := len(arr)
	for i := 0; i < n-1; i++ {
		for j := 0; j < n-i-1; j++ {
			if arr[j] > arr[j+1] {
				arr[j], arr[j+1] = arr[j+1], arr[j]
			}
		}
	}
}