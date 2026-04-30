package cache

import (
	"context"
	"sync/atomic"
	"time"
	"github.com/redis/go-redis/v9"
)

type Redis struct {
	Client *redis.Client
	Hits   int64
	Misses int64
}

func NewRedis(addr string) *Redis {
	return &Redis{Client: redis.NewClient(&redis.Options{Addr: addr})}
}

func (r *Redis) Get(ctx context.Context, key string) (string, error) {
	val, err := r.Client.Get(ctx, key).Result()
	if err == redis.Nil {
		atomic.AddInt64(&r.Misses, 1)
		return "", err
	}
	atomic.AddInt64(&r.Hits, 1)
	return val, nil
}

func (r *Redis) Set(ctx context.Context, key, val string) error {
	return r.Client.Set(ctx, key, val, time.Minute).Err()
}

func (r *Redis) Reset() {
	r.Client.FlushAll(context.Background())
	atomic.StoreInt64(&r.Hits, 0)
	atomic.StoreInt64(&r.Misses, 0)
}