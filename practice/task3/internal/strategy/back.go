package strategy

import (
	"cache-lab/internal/cache"
	"cache-lab/internal/db"
	"context"
	"sync"
	"time"
)

type WriteBack struct {
	DB    *db.Postgres
	Cache *cache.Redis
	mu    sync.Mutex
	queue map[string]string
}

func NewWriteBack(p *db.Postgres, r *cache.Redis) *WriteBack {
	wb := &WriteBack{DB: p, Cache: r, queue: make(map[string]string)}
	go wb.worker()
	return wb
}

func (s *WriteBack) Name() string { return "Write-Back" }

func (s *WriteBack) Get(ctx context.Context, key string) (string, error) {
	return s.Cache.Get(ctx, key)
}

func (s *WriteBack) Set(ctx context.Context, key, val string) error {
	s.Cache.Set(ctx, key, val)
	s.mu.Lock()
	s.queue[key] = val
	s.mu.Unlock()
	return nil
}

func (s *WriteBack) worker() {
	for {
		time.Sleep(2 * time.Second)
		s.mu.Lock()
		for k, v := range s.queue {
			s.DB.Set(k, v)
			delete(s.queue, k)
		}
		s.mu.Unlock()
	}
}