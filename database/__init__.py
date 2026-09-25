import sqlite3
import json
import os
from typing import Dict, Optional, List, Tuple


class Database:
    def __init__(self, db_path: str = "database/bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Cria as tabelas se não existirem"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela de níveis/XP
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_levels (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                multiplicador INTEGER DEFAULT 1,
                msgs_mult INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # Tabela de estatísticas do jogo Guess
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guess_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                games INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                total_attempts INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # Tabela de estatísticas do jogo Termo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS termo_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                games INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                total_attempts INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                attempts_1 INTEGER DEFAULT 0,
                attempts_2 INTEGER DEFAULT 0,
                attempts_3 INTEGER DEFAULT 0,
                attempts_4 INTEGER DEFAULT 0,
                attempts_5 INTEGER DEFAULT 0,
                attempts_6 INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        self._ensure_termo_columns(cursor)

        # Tabela de regras (opcional, para futuro)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                config_key TEXT NOT NULL,
                config_value TEXT NOT NULL,
                UNIQUE (guild_id, config_key)
            )
        """)

        conn.commit()
        conn.close()

    def _ensure_termo_columns(self, cursor):
        """Adiciona colunas novas a bases de dados já existentes (streak, distribuição)"""
        cursor.execute("PRAGMA table_info(termo_stats)")
        existing = {row[1] for row in cursor.fetchall()}
        new_columns = {
            "current_streak": "INTEGER DEFAULT 0",
            "best_streak": "INTEGER DEFAULT 0",
            "attempts_1": "INTEGER DEFAULT 0",
            "attempts_2": "INTEGER DEFAULT 0",
            "attempts_3": "INTEGER DEFAULT 0",
            "attempts_4": "INTEGER DEFAULT 0",
            "attempts_5": "INTEGER DEFAULT 0",
            "attempts_6": "INTEGER DEFAULT 0",
        }
        for column, declaration in new_columns.items():
            if column not in existing:
                cursor.execute(f"ALTER TABLE termo_stats ADD COLUMN {column} {declaration}")

    # ===== MÉTODOS DE NÍVEIS =====

    def get_user_data(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Retorna dados do usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT xp, level, multiplicador, msgs_mult FROM user_levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "xp": row[0],
                "level": row[1],
                "multiplicador": row[2],
                "msgs_mult": row[3]
            }
        return None

    def set_user_data(self, guild_id: int, user_id: int, xp: int, level: int, multiplicador: int = 1, msgs_mult: int = 0):
        """Atualiza ou insere dados do usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_levels (guild_id, user_id, xp, level, multiplicador, msgs_mult)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                xp = excluded.xp,
                level = excluded.level,
                multiplicador = excluded.multiplicador,
                msgs_mult = excluded.msgs_mult
        """, (guild_id, user_id, xp, level, multiplicador, msgs_mult))
        conn.commit()
        conn.close()

    def get_guild_users(self, guild_id: int) -> Dict[int, Dict]:
        """Retorna todos os usuários de um servidor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, xp, level, multiplicador, msgs_mult FROM user_levels WHERE guild_id = ?",
            (guild_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        result = {}
        for row in rows:
            result[row[0]] = {
                "xp": row[1],
                "level": row[2],
                "multiplicador": row[3],
                "msgs_mult": row[4]
            }
        return result

    def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Tuple[int, int, int]]:
        """Retorna o ranking do servidor (user_id, level, xp)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, level, xp FROM user_levels
            WHERE guild_id = ?
            ORDER BY level DESC, xp DESC
            LIMIT ?
        """, (guild_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return rows

    # ===== MÉTODOS DE CONFIGURAÇÃO =====

    def get_config(self, guild_id: int, key: str) -> Optional[str]:
        """Retorna uma configuração do servidor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT config_value FROM server_config WHERE guild_id = ? AND config_key = ?",
            (guild_id, key)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def set_config(self, guild_id: int, key: str, value: str):
        """Define uma configuração do servidor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO server_config (guild_id, config_key, config_value)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, config_key) DO UPDATE SET
                config_value = excluded.config_value
        """, (guild_id, key, value))
        conn.commit()
        conn.close()

    # ===== MIGRAÇÃO =====

    def migrate_from_json(self, json_path: str = "levels_data.json"):
        """Migra dados do JSON para SQLite"""
        if not os.path.exists(json_path):
            print(f"❌ Ficheiro {json_path} não encontrado")
            return False

        with open(json_path, "r") as f:
            data = json.load(f)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        migrated = 0
        for guild_id_str, users in data.items():
            guild_id = int(guild_id_str)
            for user_id_str, user_data in users.items():
                user_id = int(user_id_str)
                cursor.execute("""
                    INSERT OR REPLACE INTO user_levels (guild_id, user_id, xp, level, multiplicador, msgs_mult)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    guild_id,
                    user_id,
                    user_data.get("xp", 0),
                    user_data.get("level", 1),
                    user_data.get("multiplicador", 1),
                    user_data.get("msgs_mult", 0)
                ))
                migrated += 1

        conn.commit()
        conn.close()
        print(f"✅ Migrados {migrated} utilizadores para SQLite")
        return True

    # ===== MÉTODOS DO JOGO GUESS =====

    def get_guess_stats(self, guild_id: int, user_id: int) -> Dict:
        """Lê estatísticas do jogo Guess"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT games, wins, total_attempts FROM guess_stats WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {"games": row[0], "wins": row[1], "total_attempts": row[2]}

        return {"games": 0, "wins": 0, "total_attempts": 0}

    def set_guess_stats(self, guild_id: int, user_id: int, games: int, wins: int, total_attempts: int):
        """Grava estatísticas do jogo Guess"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO guess_stats (guild_id, user_id, games, wins, total_attempts)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                games = excluded.games,
                wins = excluded.wins,
                total_attempts = excluded.total_attempts
            """,
            (guild_id, user_id, games, wins, total_attempts)
        )
        conn.commit()
        conn.close()

    def get_guess_leaderboard(self, guild_id: int) -> List[Dict]:
        """Retorna todas as estatísticas do Guess para um servidor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, games, wins, total_attempts FROM guess_stats WHERE guild_id = ?",
            (guild_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "user_id": row[0],
                "games": row[1],
                "wins": row[2],
                "total_attempts": row[3],
            }
            for row in rows
        ]

    def migrate_guess_from_json(self, json_path: str = "data/game_data.json") -> bool:
        """Migra estatísticas antigas do Guess (JSON) para SQLite"""
        if not os.path.exists(json_path):
            return False

        with open(json_path, "r") as f:
            data = json.load(f)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        migrated = 0
        for guild_id_str, users in data.items():
            guild_id = int(guild_id_str)
            for user_id_str, stats in users.items():
                user_id = int(user_id_str)
                cursor.execute(
                    """
                    INSERT INTO guess_stats (guild_id, user_id, games, wins, total_attempts)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        games = excluded.games,
                        wins = excluded.wins,
                        total_attempts = excluded.total_attempts
                    """,
                    (
                        guild_id,
                        user_id,
                        stats.get("games", 0),
                        stats.get("wins", 0),
                        stats.get("total_attempts", 0),
                    ),
                )
                migrated += 1

        conn.commit()
        conn.close()
        print(f"✅ Migradas {migrated} estatísticas de Guess para SQLite")
        return True

    # ===== MÉTODOS DO JOGO TERMO =====

    def get_termo_stats(self, guild_id: int, user_id: int) -> Dict:
        """Lê estatísticas do jogo Termo, incluindo streak e distribuição de tentativas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT games, wins, total_attempts, current_streak, best_streak,
                   attempts_1, attempts_2, attempts_3, attempts_4, attempts_5, attempts_6
            FROM termo_stats WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "games": row[0],
                "wins": row[1],
                "total_attempts": row[2],
                "current_streak": row[3],
                "best_streak": row[4],
                "distribution": {i: row[4 + i] for i in range(1, 7)},
            }

        return {
            "games": 0, "wins": 0, "total_attempts": 0,
            "current_streak": 0, "best_streak": 0,
            "distribution": {i: 0 for i in range(1, 7)},
        }

    def set_termo_stats(
        self, guild_id: int, user_id: int, games: int, wins: int, total_attempts: int,
        current_streak: int = 0, best_streak: int = 0, distribution: Optional[Dict[int, int]] = None,
    ):
        """Grava estatísticas do jogo Termo, incluindo streak e distribuição de tentativas"""
        distribution = distribution or {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO termo_stats (
                guild_id, user_id, games, wins, total_attempts, current_streak, best_streak,
                attempts_1, attempts_2, attempts_3, attempts_4, attempts_5, attempts_6
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                games = excluded.games,
                wins = excluded.wins,
                total_attempts = excluded.total_attempts,
                current_streak = excluded.current_streak,
                best_streak = excluded.best_streak,
                attempts_1 = excluded.attempts_1,
                attempts_2 = excluded.attempts_2,
                attempts_3 = excluded.attempts_3,
                attempts_4 = excluded.attempts_4,
                attempts_5 = excluded.attempts_5,
                attempts_6 = excluded.attempts_6
            """,
            (
                guild_id, user_id, games, wins, total_attempts, current_streak, best_streak,
                distribution.get(1, 0), distribution.get(2, 0), distribution.get(3, 0),
                distribution.get(4, 0), distribution.get(5, 0), distribution.get(6, 0),
            )
        )
        conn.commit()
        conn.close()

    def get_termo_leaderboard(self, guild_id: int) -> List[Dict]:
        """Retorna todas as estatísticas do Termo para um servidor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, games, wins, total_attempts, current_streak, best_streak FROM termo_stats WHERE guild_id = ?",
            (guild_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "user_id": row[0],
                "games": row[1],
                "wins": row[2],
                "total_attempts": row[3],
                "current_streak": row[4],
                "best_streak": row[5],
            }
            for row in rows
        ]

    def migrate_termo_from_json(self, json_path: str = "data/game_data.json") -> bool:
        """Migra estatísticas antigas do Termo (JSON) para SQLite"""
        if not os.path.exists(json_path):
            return False

        with open(json_path, "r") as f:
            data = json.load(f)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        migrated = 0
        for guild_id_str, users in data.items():
            guild_id = int(guild_id_str)
            for user_id_str, stats in users.items():
                user_id = int(user_id_str)
                cursor.execute(
                    """
                    INSERT INTO termo_stats (guild_id, user_id, games, wins, total_attempts)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        games = excluded.games,
                        wins = excluded.wins,
                        total_attempts = excluded.total_attempts
                    """,
                    (
                        guild_id,
                        user_id,
                        stats.get("games", 0),
                        stats.get("wins", 0),
                        stats.get("total_attempts", 0),
                    ),
                )
                migrated += 1

        conn.commit()
        conn.close()
        print(f"✅ Migradas {migrated} estatísticas de Termo para SQLite")
        return True


__all__ = ["Database"]