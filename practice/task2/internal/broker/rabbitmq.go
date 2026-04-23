package broker

import (
	"context"
	"fmt"

	amqp "github.com/rabbitmq/amqp091-go"
)

type RabbitMQ struct {
	conn    *amqp.Connection
	channel *amqp.Channel
	queue   string
}

func NewRabbitMQ(url, queueName string) (*RabbitMQ, error) {
	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, fmt.Errorf("failed to connect: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to open channel: %w", err)
	}

	_, err = ch.QueueDeclare(
		queueName,
		false, false, false, false, nil,
	)
	if err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("failed to declare queue: %w", err)
	}

	return &RabbitMQ{
		conn:    conn,
		channel: ch,
		queue:   queueName,
	}, nil
}

func (r *RabbitMQ) Publish(ctx context.Context, msg Message) error {
	return r.channel.PublishWithContext(
		ctx,
		"",
		r.queue,
		false,
		false,
		amqp.Publishing{
			ContentType: "application/octet-stream",
			Body:        msg.Payload,
			MessageId:   msg.ID,
			Timestamp:   msg.Timestamp, // ← тут используется time.Time
		},
	)
}

func (r *RabbitMQ) Consume(ctx context.Context) (<-chan Message, <-chan error) {
	msgChan := make(chan Message, 100)
	errChan := make(chan error, 1)

	msgs, err := r.channel.Consume(
		r.queue, "", true, false, false, false, nil,
	)
	if err != nil {
		errChan <- err
		return msgChan, errChan
	}

	go func() {
		defer close(msgChan)
		defer close(errChan)

		for {
			select {
			case <-ctx.Done():
				return
			case msg, ok := <-msgs:
				if !ok {
					return
				}
				msgChan <- Message{
					ID:        msg.MessageId,
					Payload:   msg.Body,
					Timestamp: msg.Timestamp, // ← и тут
				}
			}
		}
	}()

	return msgChan, errChan
}

func (r *RabbitMQ) Close() error {
	if r.channel != nil {
		r.channel.Close()
	}
	if r.conn != nil {
		r.conn.Close()
	}
	return nil
}

func (r *RabbitMQ) Name() string {
	return "RabbitMQ"
}