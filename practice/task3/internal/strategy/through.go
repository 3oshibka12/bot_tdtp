package strategy

import (
	"cache-lab/internal/cache"
	"cache-lab/internal/db"
	"context"
)

type WriteThrough struct {
	DB    *db.Postgres
	Cache *cache.Redis
}

func (s *WriteThrough) Name() string { return "Write-Through" }

func (s *WriteThrough) Get(ctx context.Context, key string) (string, error) {
	val, err := s.Cache.Get(ctx, key)
	if err == nil { return val, nil }
	
	val, err = s.DB.Get(key)
	if err == nil { s.Cache.Set(ctx, key, val) }
	return val, err
}

func (s *WriteThrough) Set(ctx context.Context, key, val string) error {
	if err := s.DB.Set(key, val); err != nil { return err }
	return s.Cache.Set(ctx, key, val)
}