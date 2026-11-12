CREATE TABLE IF NOT EXISTS patient_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    patient_key CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    ciphertext LONGBLOB NOT NULL,
    nonce BINARY(12) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY ix_patient_records_patient_created (patient_key, created_at DESC)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;
