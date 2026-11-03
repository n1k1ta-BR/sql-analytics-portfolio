SELECT event_id,user_id,event_time,event_type
FROM events
WHERE user_id=777
ORDER BY event_time DESC
LIMIT 50;
