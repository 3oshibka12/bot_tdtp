package main

import (
	"cache-lab/internal/cache"
	"cache-lab/internal/db"
	"cache-lab/internal/strategy"
	"context"
	"fmt"
	"math/rand"
	"sync/atomic"
	"time"
)

func main() {
	// 1. Подключаемся и ЖДЕМ базу
	var pg *db.Postgres
	var err error
	for i := 0; i < 10; i++ {
		pg, err = db.NewPostgres("postgres://user:password@localhost:5433/testdb?sslmode=disable")
		if err == nil {
			err = pg.DB.Ping()
		}
		if err == nil {
			break
		}
		fmt.Println("Waiting for Postgres...")
		time.Sleep(2 * time.Second)
	}
	if err != nil {
		panic("Could not connect to Postgres")
	}

	rd := cache.NewRedis("localhost:6379")

	// 2. ЗАПОЛНЯЕМ БАЗУ (Seeding)
	fmt.Println("Seeding data...")
	for i := 0; i < 20; i++ {
		pg.Set(fmt.Sprintf("key-%d", i), "value")
	}

	strategies := []strategy.Strategy{
		&strategy.CacheAside{DB: pg, Cache: rd},
		&strategy.WriteThrough{DB: pg, Cache: rd},
		strategy.NewWriteBack(pg, rd),
	}

	scenarios := []struct {
		name  string
		readP int
	}{
		{"Read-Heavy (80/20)", 80},
		{"Balanced (50/50)", 50},
		{"Write-Heavy (20/80)", 20},
	}

	fmt.Printf("%-15s | %-20s | %-8s | %-10s | %-8s | %-8s\n", "Strategy", "Scenario", "T-put", "Avg Lat", "DB Calls", "Hit Rate")
	fmt.Println("------------------------------------------------------------------------------------------")

	for _, st := range strategies {
		for _, sc := range scenarios {
			rd.Reset()
			pg.Reset()
			
			count := 100
			start := time.Now()
			var totalLat time.Duration

			for i := 0; i < count; i++ {
				key := fmt.Sprintf("key-%d", rand.Intn(20))
				opStart := time.Now()
				
				if rand.Intn(100) < sc.readP {
					st.Get(context.Background(), key)
				} else {
					st.Set(context.Background(), key, "new_val")
				}
				totalLat += time.Since(opStart)
			}

			dur := time.Since(start)
			hits := atomic.LoadInt64(&rd.Hits)
			miss := atomic.LoadInt64(&rd.Misses)
			hitRate := 0.0
			if (hits + miss) > 0 {
				hitRate = float64(hits) / float64(hits+miss) * 100
			}

			fmt.Printf("%-15s | %-20s | %-8.1f | %-10v | %-8d | %-8.1f%%\n",
				st.Name(), sc.name, float64(count)/dur.Seconds(), totalLat/time.Duration(count), atomic.LoadInt64(&pg.Calls), hitRate)
			
			time.Sleep(3 * time.Second)
		}
	}
}