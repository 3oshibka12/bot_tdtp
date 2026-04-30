package db

import (
	"database/sql"
	"sync/atomic"
	"time"
	_ "github.com/lib/pq"
)

type Postgres struct {
	DB         *sql.DB
	ReadCalls  int64
	WriteCalls int64
}

func NewPostgres(connStr string) (*Postgres, error) {
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}
	// Проверяем соединение и создаем таблицу
	_, err = db.Exec("CREATE TABLE IF NOT EXISTS data (key TEXT PRIMARY KEY, value TEXT)")
	return &Postgres{DB: db}, err
}

func (p *Postgres) Get(key string) (string, error) {
	atomic.AddInt64(&p.ReadCalls, 1)
	time.Sleep(10 * time.Millisecond)
	var val string
	err := p.DB.QueryRow("SELECT value FROM data WHERE key = $1", key).Scan(&val)
	return val, err
}

func (p *Postgres) Set(key, val string) error {
	atomic.AddInt64(&p.WriteCalls, 1)
	time.Sleep(15 * time.Millisecond)
	_, err := p.DB.Exec("INSERT INTO data (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2", key, val)
	return err
}

func (p *Postgres) Reset() {
	atomic.StoreInt64(&p.ReadCalls, 0)
	atomic.StoreInt64(&p.WriteCalls, 0)
}