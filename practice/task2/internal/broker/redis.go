package broker

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type Redis struct {
	client *redis.Client
	queue  string
}

func NewRedis(addr, queueName string) (*Redis, error) {
	client := redis.NewClient(&redis.Options{
		Addr: addr,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect: %w", err)
	}

	return &Redis{
		client: client,
		queue:  queueName,
	}, nil
}

func (r *Redis) Publish(ctx context.Context, msg Message) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	return r.client.RPush(ctx, r.queue, data).Err()
}

func (r *Redis) Consume(ctx context.Context) (<-chan Message, <-chan error) {
	msgChan := make(chan Message, 100)
	errChan := make(chan error, 1)

	go func() {
		defer close(msgChan)
		defer close(errChan)

		for {
			select {
			case <-ctx.Done():
				return
			default:
			}

			// BLPOP с таймаутом 1 секунда
			result, err := r.client.BLPop(ctx, 1*time.Second, r.queue).Result()
			if err != nil {
				if err == redis.Nil {
					// Таймаут — нормально
					continue
				}
				if err == context.Canceled {
					return
				}
				errChan <- err
				return
			}

			if len(result) < 2 {
				continue
			}

			var msg Message
			if err := json.Unmarshal([]byte(result[1]), &msg); err != nil {
				errChan <- err
				continue
			}

			msgChan <- msg
		}
	}()

	return msgChan, errChan
}

func (r *Redis) Close() error {
	return r.client.Close()
}

func (r *Redis) Name() string {
	return "Redis"
}