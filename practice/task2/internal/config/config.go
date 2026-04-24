package config

import "time"

type Config struct {
	BrokerType      string      
	RabbitMQURL     string
	RedisAddr       string
	QueueName       string
	MessageSizes    []int         
	Rates           []int
	TestDuration    time.Duration
	NumProducers    int
	NumConsumers    int
	TotalMessages   int
}

func Default() *Config {
	return &Config{
		RabbitMQURL:   "amqp://guest:guest@localhost:5672/",
		RedisAddr:     "localhost:6379",
		QueueName:     "benchmark_queue",
		MessageSizes:  []int{128, 1024, 10240, 102400}, // 128B, 1KB, 10KB, 100KB
		Rates:         []int{1000, 5000, 10000},
		TestDuration:  30 * time.Second,
		NumProducers:  1,
		NumConsumers:  1,
		TotalMessages: 10000,
	}
}