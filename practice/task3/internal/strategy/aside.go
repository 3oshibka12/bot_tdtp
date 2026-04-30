package strategy

import (
	"cache-lab/internal/cache"
	"cache-lab/internal/db"
	"context"
)

type CacheAside struct {
	DB    *db.Postgres
	Cache *cache.Redis
}

func (s *CacheAside) Name() string { return "Cache-Aside" }

func (s *CacheAside) Get(ctx context.Context, key string) (string, error) {
	val, err := s.Cache.Get(ctx, key)
	if err == nil { return val, nil }
	
	val, err = s.DB.Get(key)
	if err == nil { s.Cache.Set(ctx, key, val) }
	return val, err
}

func (s *CacheAside) Set(ctx context.Context, key, val string) error {
	return s.DB.Set(key, val)
}