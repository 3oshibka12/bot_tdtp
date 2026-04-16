package main

import (
        "database/sql"
        "fmt"
        "log"
        "os"

		_ "github.com/lib/pq"
)

var db *sql.DB

func initDB() error {
        host := os.Getenv("DB_HOST")
        if host == "" {
                host = "localhost"
        }
        port := os.Getenv("DB_PORT")
        if port == "" {
                port = "5432"
        }
        user := os.Getenv("DB_USER")
        if user == "" {
                user = "postgres"
        }
        password := os.Getenv("DB_PASSWORD")
        if password == "" {
                password = "postgres"
        }
        dbname := os.Getenv("DB_NAME")
        if dbname == "" {
                dbname = "store"
        }

        connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
                host, port, user, password, dbname)

        var err error
        db, err = sql.Open("postgres", connStr)
        if err != nil {
                return err
        }
        return db.Ping()
}


func placeOrder(customerID int, products []struct {
        ProductID int
        Quantity  int
        Price     float64
}) (int64, error) {
        tx, err := db.Begin()
        if err != nil {
                return 0, err
        }
        defer tx.Rollback()

        var orderID int64
        err = tx.QueryRow(`
                INSERT INTO Orders (CustomerID, OrderDate, TotalAmount)
                VALUES ($1, NOW(), 0)
                RETURNING OrderID`, customerID).Scan(&orderID)
        if err != nil {
                return 0, err
        }

        var totalAmount float64
        for _, p := range products {
                subtotal := p.Price * float64(p.Quantity)
                totalAmount += subtotal

                _, err = tx.Exec(`
                        INSERT INTO OrderItems (OrderID, ProductID, Quantity, Subtotal)
                        VALUES ($1, $2, $3, $4)`,
                        orderID, p.ProductID, p.Quantity, subtotal)
                if err != nil {
                        return 0, err
                }
        }

        _, err = tx.Exec(`
                UPDATE Orders SET TotalAmount = $1 WHERE OrderID = $2`,
                totalAmount, orderID)
        if err != nil {
                return 0, err
        }

        err = tx.Commit()
        if err != nil {
                return 0, err
        }

        return orderID, nil
}


func updateCustomerEmail(customerID int, newEmail string) error {
        tx, err := db.Begin()
        if err != nil {
                return err
        }
        defer tx.Rollback()

        _, err = tx.Exec(`
                UPDATE Customers SET Email = $1 WHERE CustomerID = $2`,
                newEmail, customerID)
        if err != nil {
                return err
        }

        return tx.Commit()
}


func addProduct(productName string, price float64) (int64, error) {
        tx, err := db.Begin()
        if err != nil {
                return 0, err
        }
        defer tx.Rollback()

        var productID int64
        err = tx.QueryRow(`
                INSERT INTO Products (ProductName, Price)
                VALUES ($1, $2)
                RETURNING ProductID`,
                productName, price).Scan(&productID)
        if err != nil {
                return 0, err
        }

        err = tx.Commit()
        if err != nil {
                return 0, err
        }

        return productID, nil
}

func createTables() error {
        schema := `
        CREATE TABLE IF NOT EXISTS Customers (
                CustomerID SERIAL PRIMARY KEY,
                FirstName VARCHAR(100),
                LastName VARCHAR(100),
                Email VARCHAR(255)
        );

        CREATE TABLE IF NOT EXISTS Products (
                ProductID SERIAL PRIMARY KEY,
                ProductName VARCHAR(255),
                Price DECIMAL(10, 2)
        );

        CREATE TABLE IF NOT EXISTS Orders (
                OrderID SERIAL PRIMARY KEY,
                CustomerID INT REFERENCES Customers(CustomerID),
                OrderDate TIMESTAMP,
                TotalAmount DECIMAL(10, 2)
        );

        CREATE TABLE IF NOT EXISTS OrderItems (
                OrderItemID SERIAL PRIMARY KEY,
                OrderID INT REFERENCES Orders(OrderID),
                ProductID INT REFERENCES Products(ProductID),
                Quantity INT,
                Subtotal DECIMAL(10, 2)
        );
        `
        _, err := db.Exec(schema)
        return err
}

func main() {
        if err := initDB(); err != nil {
                log.Fatalf("Failed to connect to database: %v", err)
        }
        defer db.Close()

        if err := createTables(); err != nil {
                log.Fatalf("Failed to create tables: %v", err)
        }
        fmt.Println("Tables created successfully!")


		orderID, err := placeOrder(1, []struct {
                ProductID int
                Quantity  int
                Price     float64
        }{
                {ProductID: 1, Quantity: 2, Price: 100.0},
                {ProductID: 2, Quantity: 1, Price: 50.0},
        })
        if err != nil {
                log.Printf("Error placing order: %v", err)
        } else {
                fmt.Printf("Order placed successfully with ID: %d\n", orderID)
        }


        err = updateCustomerEmail(1, "newemail@example.com")
        if err != nil {
                log.Printf("Error updating email: %v", err)
        } else {
                fmt.Println("Customer email updated successfully!")
        }


        productID, err := addProduct("New Product", 299.99)
        if err != nil {
                log.Printf("Error adding product: %v", err)
        } else {
                fmt.Printf("Product added successfully with ID: %d\n", productID)
        }

        fmt.Println("All transactions completed!")
}