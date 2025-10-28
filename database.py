#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional


class Database:
    def __init__(self, db_path="虚词大战.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # EmptyWordAction 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empty_word_action (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empty_word TEXT NOT NULL,
                part_of_speech TEXT NOT NULL,
                action TEXT NOT NULL,
                translation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ExampleSentence 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS example_sentence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence TEXT NOT NULL,
                tags TEXT,
                empty_word TEXT NOT NULL,
                action_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_id) REFERENCES empty_word_action(id)
            )
        """)

        # Sentence_Action 关联表（一个句子可以有多个虚词用法）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentence_action (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                action_id INTEGER NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES example_sentence(id),
                FOREIGN KEY (action_id) REFERENCES empty_word_action(id),
                UNIQUE(sentence_id, action_id)
            )
        """)

        # Paper 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                question_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Question 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                sentence_id INTEGER NOT NULL,
                action_id INTEGER NOT NULL,
                question_order INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES paper(id),
                FOREIGN KEY (sentence_id) REFERENCES example_sentence(id),
                FOREIGN KEY (action_id) REFERENCES empty_word_action(id)
            )
        """)

        # Option 表（每个题目有多个选项）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_option (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                action_id INTEGER NOT NULL,
                is_correct BOOLEAN DEFAULT 0,
                option_order INTEGER NOT NULL,
                FOREIGN KEY (question_id) REFERENCES question(id),
                FOREIGN KEY (action_id) REFERENCES empty_word_action(id)
            )
        """)

        conn.commit()
        conn.close()

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # EmptyWordAction CRUD
    def create_empty_word_action(
        self, empty_word: str, part_of_speech: str, action: str, translation: str = ""
    ):
        """创建虚词用法"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO empty_word_action (empty_word, part_of_speech, action, translation)
                VALUES (?, ?, ?, ?)
            """,
                (empty_word, part_of_speech, action, translation),
            )
            return cursor.lastrowid

    def get_all_empty_word_actions(self, empty_word: Optional[str] = None):
        """获取所有虚词用法"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if empty_word:
                cursor.execute(
                    "SELECT * FROM empty_word_action WHERE empty_word = ?",
                    (empty_word,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM empty_word_action ORDER BY empty_word, id"
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_empty_word_action(self, action_id: int):
        """获取单个虚词用法"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM empty_word_action WHERE id = ?", (action_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_empty_word_action(
        self,
        action_id: int,
        empty_word: str,
        part_of_speech: str,
        action: str,
        translation: str = "",
    ):
        """更新虚词用法"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE empty_word_action
                SET empty_word = ?, part_of_speech = ?, action = ?, translation = ?
                WHERE id = ?
            """,
                (empty_word, part_of_speech, action, translation, action_id),
            )

    def delete_empty_word_action(self, action_id: int):
        """删除虚词用法"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM empty_word_action WHERE id = ?", (action_id,))

    # ExampleSentence CRUD
    def create_example_sentence(
        self, sentence: str, tags: List[str], empty_word: str, action_ids: List[int]
    ):
        """创建例句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_str = ",".join(tags) if tags else ""
            cursor.execute(
                """
                INSERT INTO example_sentence (sentence, tags, empty_word)
                VALUES (?, ?, ?)
            """,
                (sentence, tags_str, empty_word),
            )
            sentence_id = cursor.lastrowid

            # 创建句子-用法关联
            for i, action_id in enumerate(action_ids):
                cursor.execute(
                    """
                    INSERT INTO sentence_action (sentence_id, action_id)
                    VALUES (?, ?)
                """,
                    (sentence_id, action_id),
                )

            return sentence_id

    def get_all_example_sentences(
        self, empty_word: Optional[str] = None, action_id: Optional[int] = None
    ):
        """获取所有例句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT es.*, 
                       GROUP_CONCAT(DISTINCT ewa.id) as action_ids,
                       GROUP_CONCAT(DISTINCT ewa.action) as actions
                FROM example_sentence es
                LEFT JOIN sentence_action sa ON es.id = sa.sentence_id
                LEFT JOIN empty_word_action ewa ON sa.action_id = ewa.id
            """
            params = []
            conditions = []

            if empty_word:
                conditions.append("es.empty_word = ?")
                params.append(empty_word)
            if action_id:
                conditions.append("sa.action_id = ?")
                params.append(action_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " GROUP BY es.id ORDER BY es.id DESC"
            cursor.execute(query, tuple(params))

            sentences = []
            for row in cursor.fetchall():
                sentence = dict(row)
                sentence["action_ids"] = (
                    [int(id) for id in row["action_ids"].split(",")]
                    if row["action_ids"]
                    else []
                )
                sentence["actions"] = (
                    row["actions"].split(",") if row["actions"] else []
                )
                sentences.append(sentence)

            return sentences

    def get_example_sentence(self, sentence_id: int):
        """获取单个例句"""
        sentences = self.get_all_example_sentences()
        for s in sentences:
            if s["id"] == sentence_id:
                return s
        return None

    def update_example_sentence(
        self,
        sentence_id: int,
        sentence: str,
        tags: List[str],
        empty_word: str,
        action_ids: List[int],
    ):
        """更新例句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_str = ",".join(tags) if tags else ""
            cursor.execute(
                """
                UPDATE example_sentence
                SET sentence = ?, tags = ?, empty_word = ?
                WHERE id = ?
            """,
                (sentence, tags_str, empty_word, sentence_id),
            )

            # 删除旧关联
            cursor.execute(
                "DELETE FROM sentence_action WHERE sentence_id = ?", (sentence_id,)
            )

            # 创建新关联
            for action_id in action_ids:
                cursor.execute(
                    """
                    INSERT INTO sentence_action (sentence_id, action_id)
                    VALUES (?, ?)
                """,
                    (sentence_id, action_id),
                )

    def delete_example_sentence(self, sentence_id: int):
        """删除例句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sentence_action WHERE sentence_id = ?", (sentence_id,)
            )
            cursor.execute("DELETE FROM example_sentence WHERE id = ?", (sentence_id,))

    # 自动识别句子中的虚词
    def detect_empty_words_in_sentence(self, sentence: str):
        """检测句子中包含的虚词"""
        EMPTY_WORDS = [
            "而",
            "何",
            "乎",
            "乃",
            "其",
            "且",
            "若",
            "所",
            "为",
            "焉",
            "也",
            "以",
            "因",
            "于",
            "与",
            "则",
            "者",
            "之",
        ]
        found_words = []
        for word in EMPTY_WORDS:
            if word in sentence:
                found_words.append(word)
        return found_words

    # Paper 和 Question 管理
    def create_paper(self, title: str, questions: List[Dict]):
        """创建试卷"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO paper (title, question_count)
                VALUES (?, ?)
            """,
                (title, len(questions)),
            )
            paper_id = cursor.lastrowid

            for order, question in enumerate(questions, 1):
                cursor.execute(
                    """
                    INSERT INTO question (paper_id, sentence_id, action_id, question_order)
                    VALUES (?, ?, ?, ?)
                """,
                    (paper_id, question["sentence_id"], question["action_id"], order),
                )
                question_id = cursor.lastrowid

                # 添加选项
                for opt_order, option in enumerate(question.get("options", []), 1):
                    cursor.execute(
                        """
                        INSERT INTO question_option (question_id, action_id, is_correct, option_order)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            question_id,
                            option["action_id"],
                            option["is_correct"],
                            opt_order,
                        ),
                    )

            return paper_id

    def get_all_papers(self):
        """获取所有试卷"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM paper ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_paper(self, paper_id: int):
        """获取试卷详情"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM paper WHERE id = ?", (paper_id,))
            paper = dict(cursor.fetchone())

            # 获取题目
            cursor.execute(
                """
                SELECT q.*, es.sentence, sa.action_id
                FROM question q
                JOIN example_sentence es ON q.sentence_id = es.id
                LEFT JOIN sentence_action sa ON es.id = sa.sentence_id
                WHERE q.paper_id = ?
                ORDER BY q.question_order
            """,
                (paper_id,),
            )
            questions = cursor.fetchall()

            # 组装题目数据
            question_dict = {}
            for row in questions:
                q_id = row["id"]
                if q_id not in question_dict:
                    question_dict[q_id] = {
                        "id": q_id,
                        "sentence_id": row["sentence_id"],
                        "action_id": row["action_id"],
                        "sentence": row["sentence"],
                        "options": [],
                        "question_order": row["question_order"],
                    }

                # 获取选项
                cursor.execute(
                    """
                    SELECT ewa.*, qo.is_correct, qo.option_order
                    FROM question_option qo
                    JOIN empty_word_action ewa ON qo.action_id = ewa.id
                    WHERE qo.question_id = ?
                    ORDER BY qo.option_order
                """,
                    (q_id,),
                )
                options = [dict(row) for row in cursor.fetchall()]
                question_dict[q_id]["options"] = options

            paper["questions"] = list(question_dict.values())
            return paper

    def delete_paper(self, paper_id: int):
        """删除试卷"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM question WHERE paper_id = ?", (paper_id,))
            question_ids = [row[0] for row in cursor.fetchall()]

            for q_id in question_ids:
                cursor.execute(
                    "DELETE FROM question_option WHERE question_id = ?", (q_id,)
                )

            cursor.execute("DELETE FROM question WHERE paper_id = ?", (paper_id,))
            cursor.execute("DELETE FROM paper WHERE id = ?", (paper_id,))

    # 初始化数据（从JSON导入）
    def import_from_json(self, json_file: str):
        """从JSON文件导入数据"""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 导入 emptyWordActions
            for ewa in data["emptyWordActions"]:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO empty_word_action (id, empty_word, part_of_speech, action, translation)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        ewa["id"],
                        ewa["emptyWord"],
                        ewa["partOfSpeech"],
                        ewa["action"],
                        ewa.get("translation", ""),
                    ),
                )

            # 导入 exampleSentences
            for es in data["exampleSentences"]:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO example_sentence (id, sentence, empty_word)
                    VALUES (?, ?, ?)
                """,
                    (es["id"], es["sentence"], es["emptyWord"]),
                )

                # 创建句子-用法关联
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO sentence_action (sentence_id, action_id)
                    VALUES (?, ?)
                """,
                    (es["id"], es["actionId"]),
                )


if __name__ == "__main__":
    db = Database()
    # 导入初始数据
    try:
        db.import_from_json("parse/虚词数据.json")
        print("数据导入成功")
    except Exception as e:
        print(f"数据导入失败: {e}")
