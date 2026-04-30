package strategy

import "context"

type Strategy interface {
	Get(ctx context.Context, key string) (string, error)
	Set(ctx context.Context, key, val string) error
	Name() string
}