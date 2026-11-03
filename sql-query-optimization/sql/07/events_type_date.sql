SELECT COUNT(*)
FROM events
WHERE event_type='purchase'
  AND event_time >= '2024-04-01'
  AND event_time < '2024-07-01';
