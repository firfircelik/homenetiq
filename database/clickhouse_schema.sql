-- v1 opsiyonel analitik şema.
-- SQLite ana storage olarak kullanılır. ClickHouse ileride büyük hacimli zaman serisi analiz için eklenir.
CREATE TABLE IF NOT EXISTS homenetiq_metrics
(
    collected_at DateTime,
    device_id String,
    device_type String,
    metric_type String,
    quality LowCardinality(String),
    root_cause LowCardinality(String),
    rssi Nullable(Int16),
    snr Nullable(Int16),
    tx_rate_mbps Nullable(Float32),
    rx_rate_mbps Nullable(Float32),
    gateway_latency_ms Nullable(Float32),
    ap_latency_ms Nullable(Float32),
    internet_latency_ms Nullable(Float32),
    packet_loss_percent Nullable(Float32),
    jitter_ms Nullable(Float32),
    dns_latency_ms Nullable(Float32)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(collected_at)
ORDER BY (device_id, metric_type, collected_at);
