package metrics

import (
	"sort"
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
		Latencies: make([]time.Duration, 0, 100000),
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
	m.Latencies = append(m.Latencies) // Оптимизация: не аллоцируем лишний раз
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

	// Используем быструю сортировку из стандартной библиотеки
	latencies := make([]time.Duration, len(m.Latencies))
	copy(latencies, m.Latencies)
	sort.Slice(latencies, func(i, j int) bool {
		return latencies[i] < latencies[j]
	})

	var total time.Duration
	for _, l := range latencies {
		total += l
	}

	p95Index := int(float64(len(latencies)) * 0.95)
	if p95Index >= len(latencies) {
		p95Index = len(latencies) - 1
	}

	avgLatency := total / time.Duration(len(latencies))

	return Stats{
		Sent:         m.Sent,
		Received:     m.Received,
		Errors:       m.Errors,
		AvgLatencyMs: float64(avgLatency.Nanoseconds()) / 1e6,
		P95LatencyMs: float64(latencies[p95Index].Nanoseconds()) / 1e6,
		MaxLatencyMs: float64(latencies[len(latencies)-1].Nanoseconds()) / 1e6,
		Duration:     duration,
	}
}

type Stats struct {
	Sent         int64         `json:"sent"`
	Received     int64         `json:"received"`
	Errors       int64         `json:"errors"`
	AvgLatencyMs float64       `json:"avg_latency_ms"`
	P95LatencyMs float64       `json:"p95_latency_ms"`
	MaxLatencyMs float64       `json:"max_latency_ms"`
	Duration     time.Duration `json:"duration"`
}

func (s Stats) Throughput() float64 {
	if s.Duration.Seconds() == 0 {
		return 0
	}
	return float64(s.Received) / s.Duration.Seconds()
}