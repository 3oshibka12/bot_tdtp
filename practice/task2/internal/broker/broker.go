package broker

import (
	"context"
	"time"
)

// Message представляет сообщение
type Message struct {
	ID        string
	Payload   []byte
	Timestamp time.Time
}

// Broker — общий интерфейс для брокеров
type Broker interface {
	// Publish отправляет сообщение
	Publish(ctx context.Context, msg Message) error
	
	// Consume читает сообщения из очереди
	Consume(ctx context.Context) (<-chan Message, <-chan error)
	
	// Close закрывает соединение
	Close() error
	
	// Name возвращает название брокера
	Name() string
}

// Stats — статистика обработки
type Stats struct {
	Sent       int64
	Received   int64
	Errors     int64
	AvgLatency time.Duration
	P95Latency time.Duration
	MaxLatency time.Duration
}