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
	pg, err := db.NewPostgres("postgres://user:password@localhost:5433/testdb?sslmode=disable")
	if err != nil { panic(err) }
	rd := cache.NewRedis("localhost:6379")

	fmt.Println("Seeding database...")
	for i := 0; i < 100; i++ {
		pg.Set(fmt.Sprintf("key-%d", i), "init")
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
		{"Read-Heavy", 80},
		{"Balanced", 50},
		{"Write-Heavy", 20},
	}

	fmt.Printf("%-15s | %-12s | %-8s | %-10s | %-7s | %-7s | %-8s\n", 
		"Strategy", "Scenario", "T-put", "Avg Lat", "DB Rd", "DB Wr", "HitRate")
	fmt.Println("---------------------------------------------------------------------------------------------")

	for _, st := range strategies {
		for _, sc := range scenarios {
			rd.Reset()
			pg.Reset()
			
			count := 1000
			start := time.Now()
			var totalLat time.Duration

			for i := 0; i < count; i++ {
				key := fmt.Sprintf("key-%d", rand.Intn(100))
				opStart := time.Now()
				
				if rand.Intn(100) < sc.readP {
					st.Get(context.Background(), key)
				} else {
					st.Set(context.Background(), key, "val")
				}
				totalLat += time.Since(opStart)
			}

			if st.Name() == "Write-Back" {
				time.Sleep(1200 * time.Millisecond)
			}

			dur := time.Since(start)
			hits := atomic.LoadInt64(&rd.Hits)
			miss := atomic.LoadInt64(&rd.Misses)
			
			hitRate := 0.0
			if (hits + miss) > 0 { hitRate = float64(hits) / float64(hits+miss) * 100 }

			tPut := float64(count) / dur.Seconds()
			avgLat := totalLat / time.Duration(count)
			dbRd := atomic.LoadInt64(&pg.ReadCalls)
			dbWr := atomic.LoadInt64(&pg.WriteCalls)

			fmt.Printf("%-15s | %-12s | %-8.1f | %-10v | %-7d | %-7d | %-8.1f%%\n",
				st.Name(), sc.name, tPut, avgLat, dbRd, dbWr, hitRate)
			
			time.Sleep(500 * time.Millisecond)
		}
	}
}