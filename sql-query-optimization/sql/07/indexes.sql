CREATE INDEX orders_status_date ON orders(status,order_date);
CREATE INDEX event_time ON events(user_id, event_time DESC);
CREATE INDEX event_type_time ON events(event_type, event_time);
