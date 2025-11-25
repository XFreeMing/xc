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

        # Sentence 表（句子基础表）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence TEXT NOT NULL UNIQUE,
                nos TEXT NOT NULL,
                tags TEXT
            )
        """)

        # ExampleSentence 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS example_sentence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                empty_word TEXT NOT NULL,
                action_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sentence_id) REFERENCES sentence(id),
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

    # Sentence CRUD
    def create_sentence(self, sentence: str, nos: List[int], tags: List[str] = None):
        """创建句子"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            nos_str = ",".join(map(str, nos))
            tags_str = ",".join(tags) if tags else ""

            cursor.execute(
                """
                INSERT OR REPLACE INTO sentence (sentence, nos, tags)
                VALUES (?, ?, ?)
            """,
                (sentence, nos_str, tags_str),
            )
            return cursor.lastrowid

    def get_all_sentences(self, empty_word_filter: Optional[str] = None):
        """获取所有句子，支持虚词模糊搜索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if empty_word_filter:
                # 如果指定了虚词，查找包含该虚词的句子
                cursor.execute(
                    """
                    SELECT DISTINCT s.* 
                    FROM sentence s
                    JOIN example_sentence es ON s.id = es.sentence_id
                    WHERE es.empty_word = ?
                    ORDER BY s.id
                """,
                    (empty_word_filter,),
                )
            else:
                cursor.execute("SELECT * FROM sentence ORDER BY id")

            sentences = []
            for row in cursor.fetchall():
                sentence = dict(row)
                sentence["nos"] = (
                    [int(n) for n in row["nos"].split(",")] if row["nos"] else []
                )
                sentence["tags"] = row["tags"].split(",") if row["tags"] else []
                sentences.append(sentence)

            return sentences

    def update_sentence(
        self, sentence_id: int, sentence: str, nos: List[int], tags: List[str] = None
    ):
        """更新句子"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            nos_str = ",".join(map(str, nos))
            tags_str = ",".join(tags) if tags else ""

            cursor.execute(
                """
                UPDATE sentence
                SET sentence = ?, nos = ?, tags = ?
                WHERE id = ?
            """,
                (sentence, nos_str, tags_str, sentence_id),
            )

    def delete_sentence(self, sentence_id: int):
        """删除句子"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM example_sentence WHERE sentence_id = ?", (sentence_id,)
            )
            cursor.execute("DELETE FROM sentence WHERE id = ?", (sentence_id,))

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
        self, empty_words: List[str] = None, action_id: Optional[int] = None
    ):
        """获取所有例句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT es.*, 
                       s.sentence,
                       GROUP_CONCAT(DISTINCT ewa.id) as action_ids,
                       GROUP_CONCAT(DISTINCT ewa.action) as actions
                FROM example_sentence es
                LEFT JOIN sentence s ON es.sentence_id = s.id
                LEFT JOIN sentence_action sa ON es.id = sa.sentence_id
                LEFT JOIN empty_word_action ewa ON sa.action_id = ewa.id
            """
            params = []
            conditions = []

            if empty_words:
                placeholders = ",".join(["?"] * len(empty_words))
                conditions.append(f"es.empty_word IN ({placeholders})")
                params.extend(empty_words)
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

    # 初始化数据（从"所有句子.md"导入）
    def import_from_markdown(self, md_file: str):
        """从Markdown文件导入句子数据，并进行深度去重"""
        import re

        def normalize_text(text):
            return re.sub(r"[^\w\u4e00-\u9fa5]", "", text)

        # 句子字典，用于处理重复
        # key: normalized_text, value: {sentence: original_text, nos: [], tags: []}
        temp_sentences = {}

        with open(md_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 匹配格式：序号. 句子内容
                match = re.match(r"^(\d+)\.\s+(.+)$", line)
                if match:
                    no = int(match.group(1))
                    sentence = match.group(2).strip()
                    norm_text = normalize_text(sentence)

                    if norm_text in temp_sentences:
                        # 如果已存在，保留长度较长的版本
                        if len(sentence) > len(temp_sentences[norm_text]["sentence"]):
                            temp_sentences[norm_text]["sentence"] = sentence
                        temp_sentences[norm_text]["nos"].append(no)
                    else:
                        temp_sentences[norm_text] = {
                            "sentence": sentence,
                            "nos": [no],
                            "tags": [],
                        }

        # 处理包含关系（子集去重）
        # 先按长度降序排序
        sorted_items = sorted(
            temp_sentences.items(),
            key=lambda x: len(normalize_text(x[1]["sentence"])),
            reverse=True,
        )

        final_sentences_dict = {}  # key: sentence (original), value: nos
        kept_normalized_texts = []

        for norm_text, data in sorted_items:
            # 检查是否是已保留句子的子集
            is_subset = False
            for kept_norm in kept_normalized_texts:
                if norm_text in kept_norm:
                    is_subset = True
                    break

            if not is_subset:
                final_sentences_dict[data["sentence"]] = data["nos"]
                kept_normalized_texts.append(norm_text)
            else:
                print(f"Skipping subset sentence: {data['sentence']}")

        # 导入到数据库
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for sentence, nos in final_sentences_dict.items():
                nos_str = ",".join(map(str, nos))
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO sentence (sentence, nos, tags)
                    VALUES (?, ?, ?)
                """,
                    (sentence, nos_str, ""),
                )
        print(f"成功导入 {len(final_sentences_dict)} 个去重后的句子")

    # 初始化数据（从JSON导入）
    def import_from_json(self, json_file: str):
        """从JSON文件导入数据"""
        print("暂时跳过 JSON 数据导入（数据文件缺失）")
        return
        # 原有的导入逻辑暂时注释掉
        """
        import re

        def normalize_text(text):
            # 去除所有空白和标点符号
            return re.sub(r"[^\w\u4e00-\u9fa5]", "", text)

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # ... (rest of the code)
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. 导入 emptyWordActions（虚词定义）
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

            # 添加一个默认的 UNKNOWN 动作，ID 0
            cursor.execute(
                """
                INSERT OR IGNORE INTO empty_word_action (id, empty_word, part_of_speech, action, translation)
                VALUES (0, 'UNKNOWN', 'UNKNOWN', '待补充', '')
                """
            )

            # 2. 获取所有现有句子（已从markdown导入），构建 normalized -> id 映射
            cursor.execute("SELECT id, sentence FROM sentence")
            sentence_rows = cursor.fetchall()
            sentence_map = {
                normalize_text(row["sentence"]): row["id"] for row in sentence_rows
            }
            existing_sentences_set = set(sentence_map.keys())

            # 3. 导入 JSON 中的 exampleSentences (已知配置的句子)
            # 同时记录哪些句子已经被配置了
            configured_sentences_set = set()

            for es in data["exampleSentences"]:
                normalized_sentence = normalize_text(es["sentence"])

                # 尝试查找句子ID
                sentence_id = None

                # 1. 精确匹配
                if normalized_sentence in sentence_map:
                    sentence_id = sentence_map[normalized_sentence]
                else:
                    # 2. 尝试模糊匹配/包含匹配
                    # 遍历所有现有句子，检查 JSON 句子是否是现有句子的子集
                    # 或者现有句子是 JSON 句子的子集（如果是后者，可能需要更新数据库，但简单起见我们优先保留已有的长句子）

                    best_match_id = None
                    best_match_len = 0

                    for existing_norm, existing_id in sentence_map.items():
                        # Case A: JSON 句子是现有句子的子集 (e.g. JSON="仰观宇宙", DB="仰观宇宙之大")
                        if normalized_sentence in existing_norm:
                            # 找到了一个父句子，使用这个父句子ID
                            sentence_id = existing_id
                            break

                        # Case B: 现有句子是 JSON 句子的子集 (e.g. JSON="仰观宇宙之大", DB="仰观宇宙")
                        # 这种情况比较少见，因为我们已经导入了最完整的 Markdown 数据
                        # 但如果发生了，我们可以认为匹配上了，但继续使用数据库里的那个（为了ID稳定性）
                        if existing_norm in normalized_sentence:
                            # 找到了一个子句子，暂时记录下来，如果没找到父句子，就用这个
                            if len(existing_norm) > best_match_len:
                                best_match_id = existing_id
                                best_match_len = len(existing_norm)

                    if not sentence_id and best_match_id:
                        sentence_id = best_match_id

                    if not sentence_id:
                        # 3. 确实找不到，且没有包含关系
                        # 策略修改：严格只使用 Markdown 中的句子，不从 JSON 插入新句子
                        # print(f"Info: Skipping JSON-only sentence (not in markdown): {es['sentence']}")
                        pass

                # 记录配置
                if sentence_id:
                    # 获取该ID对应的标准化文本（可能是长句子的）
                    cursor.execute(
                        "SELECT sentence FROM sentence WHERE id = ?", (sentence_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        actual_sentence = row[0]
                        configured_sentences_set.add(normalize_text(actual_sentence))

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO example_sentence (id, sentence_id, empty_word)
                        VALUES (?, ?, ?)
                    """,
                        (es["id"], sentence_id, es["emptyWord"]),
                    )

                # 创建句子-用法关联
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO sentence_action (sentence_id, action_id)
                    VALUES (?, ?)
                """,
                    (es["id"], es["actionId"]),
                )

            # 4. 遍历检查所有 MD 中的句子，找出未配置的句子
            # 自动识别其中的虚词，并添加为默认配置（action_id=0）
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

            count_auto_added = 0
            for row in sentence_rows:
                original_text = row["sentence"]
                norm_text = normalize_text(original_text)

                if norm_text not in configured_sentences_set:
                    # 这是一个未配置的句子
                    # 自动检测包含哪些虚词
                    found_words = []
                    for word in EMPTY_WORDS:
                        if word in original_text:
                            found_words.append(word)

                    if found_words:
                        sentence_id = row["id"]
                        print(
                            f"Auto-configuring sentence: {original_text} -> Found: {found_words}"
                        )

                        for word in found_words:
                            # 插入 example_sentence
                            cursor.execute(
                                "INSERT INTO example_sentence (sentence_id, empty_word) VALUES (?, ?)",
                                (sentence_id, word),
                            )
                            es_id = cursor.lastrowid

                            # 插入关联，使用默认ID 0
                            cursor.execute(
                                "INSERT INTO sentence_action (sentence_id, action_id) VALUES (?, 0)",
                                (es_id,),
                            )
                        count_auto_added += 1
                    else:
                        print(
                            f"Skipping sentence (no empty words found): {original_text}"
                        )

            print(
                f"自动补充了 {count_auto_added} 个未配置句子的虚词记录（Action ID = 0）"
            )


if __name__ == "__main__":
    db = Database()
    # 导入初始数据
    try:
        # 先导入所有句子
        db.import_from_markdown("parse/所有句子.md")
        # 再导入虚词数据和例句关联
        db.import_from_json("parse/虚词数据.json")
        print("数据导入成功")
    except Exception as e:
        print(f"数据导入失败: {e}")
        import traceback

        traceback.print_exc()
