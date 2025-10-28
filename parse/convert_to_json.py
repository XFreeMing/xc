#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from typing import Dict, List


def parse_markdown_to_json(filename: str = "虚词资料.md") -> Dict:
    """
    解析虚词资料Markdown文件，转换为JSON格式

    格式：
    ## [汉字序号]、[虚词]

    ### [词性]

    1. [作用]:[意思]
       - [对应例句]
       - [对应例句]
    """

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # 虚词映射表
    word_map = {
        "一": "而",
        "二": "何",
        "三": "乎",
        "四": "乃",
        "五": "其",
        "六": "且",
        "七": "若",
        "八": "所",
        "九": "为",
        "十": "焉",
        "十一": "也",
        "十二": "以",
        "十三": "因",
        "十四": "于",
        "十五": "与",
        "十六": "则",
        "十七": "者",
        "十八": "之",
    }

    # 词性枚举映射
    pos_map = {
        "连词": "CONJUNCTION",
        "副词": "ADVERB",
        "介词": "PREPOSITION",
        "代词": "PRONOUN",
        "疑问代词": "PRONOUN",
        "疑问副词": "ADVERB",
        "动词": "VERB",
        "名词": "NOUN",
        "语气助词": "PARTICLE",
        "句末语气词": "PARTICLE",
        "句中语气词": "PARTICLE",
        "语气词": "PARTICLE",
        "形容词": "ADJECTIVE",
        "助词": "AUXILIARY",
        "复音虚词": "AUXILIARY",
        "副音虚词": "AUXILIARY",
        "兼词": "PRONOUN",
        "指示代词": "PRONOUN",
        "第三人称代词": "PRONOUN",
        "形容词词尾": "PARTICLE",
    }

    empty_word_actions = []
    example_sentences = []

    action_id = 1
    sentence_id = 1

    # 跳过开头的标题行 (# 虚词资料)
    # 按双井号分割每个虚词
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)

    for section in sections:
        # 跳过第一个可能包含文件标题的部分
        if not re.match(r"([一二三四五六七八九十]+)、", section):
            continue
        # 提取虚词序号和名称
        # 格式：一、而
        title_match = re.match(
            r"([一二三四五六七八九十]+)、(.+)", section.split("\n")[0]
        )
        if not title_match:
            continue

        word_sequence = title_match.group(1)
        word_name = word_map.get(word_sequence, "")

        if not word_name:
            continue

        # 提取每个词性段落
        # 格式：### 连词
        pos_paragraphs = re.split(r"^###\s+(.+)$", section, flags=re.MULTILINE)

        # re.split的返回值结构：[分割符前的部分, 分割符匹配的内容, 分割符后的内容, ...]
        # 所以跳过第一个元素（标题），然后每两个元素组成一组（词性名+内容）
        for i in range(1, len(pos_paragraphs), 2):
            if i + 1 >= len(pos_paragraphs):
                break

            pos_name = pos_paragraphs[i].strip()
            pos_content = pos_paragraphs[i + 1]

            # 提取词性枚举
            pos_enum = pos_map.get(pos_name, pos_name.upper())

            # 提取用法段落
            # 格式：
            # 1. 并列：又
            #    - 例句1
            # 例句2
            usage_pattern = r"(\d+)\.\s*([^:：\n]+)[:：]([^\n]+)"

            for usage_match in re.finditer(usage_pattern, pos_content, re.MULTILINE):
                usage_num = usage_match.group(1)
                action_text = usage_match.group(2).strip()
                translation = usage_match.group(3).strip()

                # 获取该用法的全部内容（用于提取例句）
                usage_start = usage_match.start()
                # 查找下一个用法的位置
                next_usage_match = re.search(
                    r"\d+\.\s*", pos_content[usage_match.end() :]
                )
                if next_usage_match:
                    usage_end = usage_match.end() + next_usage_match.start()
                else:
                    usage_end = len(pos_content)

                usage_block = pos_content[usage_start:usage_end]

                empty_word_actions.append(
                    {
                        "id": action_id,
                        "emptyWord": word_name,
                        "partOfSpeech": pos_enum,
                        "action": action_text,
                        "translation": translation,
                    }
                )

                # 提取该用法下的例句
                # 格式：- 例句文本
                sentence_pattern = r"-\s*(.+?)(?=\n\s*-|\n\d+\.|\n###|$)"
                sentences = re.findall(sentence_pattern, usage_block)

                for sentence in sentences:
                    sent = sentence.strip()
                    if sent:
                        example_sentences.append(
                            {
                                "id": sentence_id,
                                "sentence": sent,
                                "emptyWord": word_name,
                                "actionId": action_id,
                            }
                        )
                        sentence_id += 1

                action_id += 1

    return {
        "emptyWordActions": empty_word_actions,
        "exampleSentences": example_sentences,
    }


if __name__ == "__main__":
    try:
        # 解析文件
        data = parse_markdown_to_json("虚词资料.md")

        # 输出JSON
        output_file = "虚词数据.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ 成功解析 {len(data['emptyWordActions'])} 个虚词用法")
        print(f"✓ 成功解析 {len(data['exampleSentences'])} 个例句")
        print(f"\n数据已保存到: {output_file}")

        # 统计各虚词数量
        from collections import Counter

        word_counts = Counter(
            action["emptyWord"] for action in data["emptyWordActions"]
        )

        print("\n各虚词用法统计:")
        for word in sorted(word_counts.keys()):
            print(f"  {word}: {word_counts[word]} 个用法")

    except FileNotFoundError:
        print(f"错误: 找不到文件 '虚词资料.md'")
        print("请确保文件在当前目录")
    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()
