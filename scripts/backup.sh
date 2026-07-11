#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║      Quant-Nanggroe-AI  —  Automated Backup Script                 ║
# ║      Database, Config, Logs | Rotation Policy | S3 Upload          ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
DATE_STAMP="$(date +%Y%m%d)"

# Retention policy
DAILY_KEEP="${DAILY_KEEP:-7}"
WEEKLY_KEEP="${WEEKLY_KEEP:-4}"

# Database
DB_URL="${QNAI_DATABASE_URL:-sqlite:///data/quant.db}"
DB_TYPE="sqlite"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-quant_nanggroe}"
DB_USER="${POSTGRES_USER:-qna}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

# S3 upload
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
S3_PREFIX="${S3_BACKUP_PREFIX:-qnai/backups}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── Helpers ────────────────────────────────────────────────────────────
log()    { echo -e "${BLUE}[BACKUP]${NC} $*"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()    { echo -e "${RED}[ERROR]${NC} $*" >&2; }
success(){ echo -e "${GREEN}[OK]${NC} $*"; }
die()    { err "$*"; exit 1; }

mkdir -p "$BACKUP_DIR"/{daily,weekly,logs,config,db}

# ── Database Detection ─────────────────────────────────────────────────
detect_db_type() {
    if [[ "$DB_URL" == postgresql* ]] || [[ "$DB_URL" == postgres* ]]; then
        DB_TYPE="postgresql"
    elif [[ "$DB_URL" == sqlite* ]]; then
        DB_TYPE="sqlite"
    elif [[ "$DB_URL" == mysql* ]]; then
        DB_TYPE="mysql"
    else
        warn "Unknown DB URL scheme, defaulting to sqlite"
        DB_TYPE="sqlite"
    fi
    log "Detected database type: $DB_TYPE"
}

# ── Database Backup ────────────────────────────────────────────────────
backup_database() {
    log "═══ Backing up database ═══"
    local dest="$BACKUP_DIR/db/db-$TIMESTAMP.sql.gz"

    case "$DB_TYPE" in
        postgresql)
            if [ -n "$DB_PASSWORD" ]; then
                PGPASSWORD="$DB_PASSWORD" pg_dump \
                    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                    --no-owner --no-acl \
                    | gzip > "$dest" 2>/dev/null
            else
                pg_dump \
                    -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" \
                    --no-owner --no-acl \
                    | gzip > "$dest" 2>/dev/null
            fi
            ;;
        sqlite)
            local db_path
            db_path=$(echo "$DB_URL" | sed 's|sqlite:///||')
            if [ -f "$PROJECT_DIR/$db_path" ]; then
                sqlite3 "$PROJECT_DIR/$db_path" .dump | gzip > "$dest"
            else
                # Fallback: just copy the file
                cp "$PROJECT_DIR/$db_path" "$dest"
            fi
            ;;
        mysql)
            mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
                ${DB_PASSWORD:+-p"$DB_PASSWORD"} "$DB_NAME" \
                | gzip > "$dest" 2>/dev/null
            ;;
    esac

    if [ -f "$dest" ] && [ -s "$dest" ]; then
        local size
        size=$(du -h "$dest" | cut -f1)
        success "Database backup: $dest ($size)"
    else
        die "Database backup failed"
    fi
}

# ── Configuration Backup ───────────────────────────────────────────────
backup_config() {
    log "═══ Backing up configuration ═══"
    local dest="$BACKUP_DIR/config/config-$TIMESTAMP.tar.gz"

    tar -czf "$dest" \
        -C "$PROJECT_DIR" \
        .env \
        config/ \
        docker-compose.yml \
        docker-compose.monitoring.yml \
        e2b.toml \
        alembic.ini \
        nginx/ \
        monitoring/prometheus.yml \
        monitoring/prometheus/alert_rules.yml \
        2>/dev/null || warn "Some config files may not exist"

    if [ -f "$dest" ]; then
        local size
        size=$(du -h "$dest" | cut -f1)
        success "Config backup: $dest ($size)"
    else
        warn "Config backup empty or failed"
    fi
}

# ── Log Backup ─────────────────────────────────────────────────────────
backup_logs() {
    log "═══ Backing up logs ═══"
    local dest="$BACKUP_DIR/logs/logs-$TIMESTAMP.tar.gz"
    local log_dirs=()

    # Collect existing log directories
    for dir in "$PROJECT_DIR/logs" "$PROJECT_DIR/data/logs" /var/log/qna*; do
        if [ -d "$dir" ]; then
            log_dirs+=("$dir")
        fi
    done

    # Also backup journal logs if systemd
    if command -v journalctl &>/dev/null; then
        local journal_dest="$BACKUP_DIR/logs/journal-$TIMESTAMP.log"
        journalctl -u quant-nanggroe-ai --since "7 days ago" --no-pager > "$journal_dest" 2>/dev/null || true
    fi

    if [ ${#log_dirs[@]} -gt 0 ]; then
        tar -czf "$dest" "${log_dirs[@]}" 2>/dev/null || true
        if [ -f "$dest" ]; then
            local size
            size=$(du -h "$dest" | cut -f1)
            success "Log backup: $dest ($size)"
        fi
    else
        warn "No log directories found to backup"
    fi
}

# ── Rotation Policy ────────────────────────────────────────────────────
rotate_backups() {
    log "═══ Rotating backups ═══"

    # Keep last N daily backups
    local daily_count
    daily_count=$(find "$BACKUP_DIR/db" -name "*.gz" -type f | wc -l)
    if [ "$daily_count" -gt "$DAILY_KEEP" ]; then
        local to_remove=$((daily_count - DAILY_KEEP))
        log "Removing $to_remove old daily backups (keeping $DAILY_KEEP)..."
        find "$BACKUP_DIR/db" -name "*.gz" -type f -printf '%T@ %p\n' \
            | sort -n | head -n "$to_remove" | awk '{print $2}' \
            | xargs rm -f
        find "$BACKUP_DIR/config" -name "*.gz" -type f -printf '%T@ %p\n' \
            | sort -n | head -n "$to_remove" | awk '{print $2}' \
            | xargs rm -f 2>/dev/null || true
    fi

    # Weekly rotation: every Sunday, keep 4 weeks
    if [ "$(date +%u)" -eq 7 ]; then
        log "Sunday — creating weekly snapshot..."
        for dir in db config logs; do
            local weekly_dest="$BACKUP_DIR/weekly/"
            mkdir -p "$weekly_dest"
            find "$BACKUP_DIR/$dir" -name "*$DATE_STAMP*" -type f -exec cp {} "$weekly_dest/" \;
        done

        local weekly_count
        weekly_count=$(find "$BACKUP_DIR/weekly" -type f | wc -l)
        if [ "$weekly_count" -gt "$((WEEKLY_KEEP * 10))" ]; then
            log "Rotating weekly backups..."
            find "$BACKUP_DIR/weekly" -type f -printf '%T@ %p\n' \
                | sort -n | head -n "$((weekly_count - WEEKLY_KEEP * 10))" \
                | awk '{print $2}' | xargs rm -f
        fi
    fi

    success "Rotation complete"
}

# ── S3 Upload ──────────────────────────────────────────────────────────
upload_s3() {
    if [ -z "$S3_BUCKET" ]; then
        log "No S3 bucket configured — skipping upload"
        return 0
    fi

    if ! command -v aws &>/dev/null; then
        warn "AWS CLI not found — skipping S3 upload"
        return 0
    fi

    log "═══ Uploading to S3: s3://$S3_BUCKET/$S3_PREFIX/$DATE_STAMP/ ═══"
    local upload_path="s3://$S3_BUCKET/$S3_PREFIX/$DATE_STAMP/"

    aws s3 cp "$BACKUP_DIR/db/" "$upload_path/db/" \
        --region "$AWS_REGION" \
        --recursive \
        --storage-class STANDARD_IA \
        2>&1 | tee -a /tmp/qna-backup.log

    aws s3 cp "$BACKUP_DIR/config/" "$upload_path/config/" \
        --region "$AWS_REGION" \
        --recursive \
        --storage-class STANDARD_IA \
        2>&1 | tee -a /tmp/qna-backup.log

    success "S3 upload complete: $upload_path"
}

# ── Report ─────────────────────────────────────────────────────────────
backup_report() {
    log "═══ Backup Report ═══"
    echo ""
    echo "  Timestamp:  $TIMESTAMP"
    echo "  Database:   $BACKUP_DIR/db/db-$TIMESTAMP.sql.gz"
    echo "  Config:     $BACKUP_DIR/config/config-$TIMESTAMP.tar.gz"
    echo "  Logs:       $BACKUP_DIR/logs/"
    echo ""
    echo "  Backup sizes:"
    du -sh "$BACKUP_DIR"/* 2>/dev/null || echo "    (none)"
    echo ""
    echo "  Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
}

# ── Usage ──────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $0 [command]

Commands:
    all         Run full backup (db + config + logs + rotate + upload)
    db          Backup database only
    config      Backup configuration only
    logs        Backup logs only
    rotate      Run rotation policy
    upload      Upload to S3
    report      Show backup report
    help        Show this help

Environment Variables:
    BACKUP_DIR          Backup output directory
    DAILY_KEEP          Number of daily backups to retain (default: 7)
    WEEKLY_KEEP         Number of weekly backups to retain (default: 4)
    S3_BACKUP_BUCKET    S3 bucket name for uploads
    S3_BACKUP_PREFIX    S3 key prefix (default: qnai/backups)
    AWS_REGION          AWS region (default: us-east-1)
    QNAI_DATABASE_URL   Database connection URL
    POSTGRES_DB         PostgreSQL database name
    POSTGRES_USER       PostgreSQL user
    POSTGRES_PASSWORD   PostgreSQL password
EOF
}

# ── Main ───────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-all}"

    log "Quant Nanggroe AI — Backup Script"
    log "Timestamp: $TIMESTAMP"
    log "Backup directory: $BACKUP_DIR"

    detect_db_type

    case "$cmd" in
        all)
            backup_database
            backup_config
            backup_logs
            rotate_backups
            upload_s3
            backup_report
            ;;
        db)      backup_database ;;
        config)  backup_config ;;
        logs)    backup_logs ;;
        rotate)  rotate_backups ;;
        upload)  upload_s3 ;;
        report)  backup_report ;;
        help|--help|-h) usage ;;
        *)       die "Unknown command: $cmd. Run '$0 help' for usage." ;;
    esac

    success "Backup operation complete"
}

main "$@"
