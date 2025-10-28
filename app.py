#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from datetime import datetime

import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from database import Database

# 页面配置必须在所有 Streamlit 命令之前
st.set_page_config(
    page_title="虚词大战 - 教师端", layout="wide", initial_sidebar_state="expanded"
)

# 虚词列表
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

# 词性列表（存储用英文）
PART_OF_SPEECH = [
    "VERB",
    "NOUN",
    "ADJECTIVE",
    "ADVERB",
    "PREPOSITION",
    "CONJUNCTION",
    "PRONOUN",
    "ARTICLE",
    "PARTICLE",
    "AUXILIARY",
]

# 词性英文到中文的映射
PART_OF_SPEECH_ZH = {
    "VERB": "动词",
    "NOUN": "名词",
    "ADJECTIVE": "形容词",
    "ADVERB": "副词",
    "PREPOSITION": "介词",
    "CONJUNCTION": "连词",
    "PRONOUN": "代词",
    "ARTICLE": "冠词",
    "PARTICLE": "语气词",
    "AUXILIARY": "助词",
}

# 词性中文到英文的映射（反向）
PART_OF_SPEECH_EN = {v: k for k, v in PART_OF_SPEECH_ZH.items()}


def get_pos_display(pos_code: str) -> str:
    """获取词性的中文显示"""
    return PART_OF_SPEECH_ZH.get(pos_code, pos_code)


# 初始化数据库
@st.cache_resource
def get_db():
    return Database()


db = get_db()

# 侧边栏
st.sidebar.title("虚词大战")
st.sidebar.markdown("---")

page = st.sidebar.radio("选择功能", ["数据管理", "例句管理", "试卷生成", "试卷列表"])

if page == "数据管理":
    st.title("虚词用法管理")

    tab1, tab2 = st.tabs(["查看所有", "添加新用法"])

    with tab1:
        # 筛选条件
        col1, col2 = st.columns(2)
        with col1:
            filter_empty_word = st.selectbox("筛选虚词", [None] + EMPTY_WORDS)
        with col2:
            col2.markdown("<br>", unsafe_allow_html=True)
            if st.button("清除筛选"):
                filter_empty_word = None
                st.rerun()

        # 获取数据
        actions = db.get_all_empty_word_actions(filter_empty_word)

        st.markdown(f"### 共 {len(actions)} 个虚词用法")

        # 显示表格
        for action in actions:
            pos_display = get_pos_display(action["part_of_speech"])
            with st.expander(
                f"{action['empty_word']} - {action['action']} ({pos_display})"
            ):
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(f"**虚词**: {action['empty_word']}")
                    st.markdown(f"**词性**: {pos_display}")
                    st.markdown(f"**用法**: {action['action']}")
                    st.markdown(f"**翻译**: {action['translation']}")

                with col2:
                    pass

                with col3:
                    if st.button("删除", key=f"delete_{action['id']}"):
                        db.delete_empty_word_action(action["id"])
                        st.success(f"已删除")
                        st.rerun()

                # 内联编辑
                st.markdown("**修改**:")
                with st.form(key=f"edit_form_{action['id']}"):
                    col_empty, col_pos = st.columns(2)
                    with col_empty:
                        edit_empty_word = st.selectbox(
                            "虚词",
                            EMPTY_WORDS,
                            index=EMPTY_WORDS.index(action["empty_word"]),
                            key=f"ew_{action['id']}",
                        )
                    with col_pos:
                        # 显示中文，但存储英文
                        pos_options_zh = [
                            get_pos_display(pos) for pos in PART_OF_SPEECH
                        ]
                        selected_zh = get_pos_display(action["part_of_speech"])
                        edit_part_of_speech_zh = st.selectbox(
                            "词性",
                            pos_options_zh,
                            index=pos_options_zh.index(selected_zh)
                            if selected_zh in pos_options_zh
                            else 0,
                            key=f"pos_{action['id']}",
                        )
                        edit_part_of_speech = PART_OF_SPEECH_EN[edit_part_of_speech_zh]
                    edit_action = st.text_input(
                        "用法", action["action"], key=f"act_{action['id']}"
                    )
                    edit_translation = st.text_input(
                        "翻译", action["translation"], key=f"trans_{action['id']}"
                    )
                    if st.form_submit_button("更新"):
                        db.update_empty_word_action(
                            action["id"],
                            edit_empty_word,
                            edit_part_of_speech,
                            edit_action,
                            edit_translation,
                        )
                        st.success("已更新")
                        st.rerun()

    with tab2:
        st.markdown("### 添加新虚词用法")

        col1, col2 = st.columns(2)
        with col1:
            new_empty_word = st.selectbox("虚词", EMPTY_WORDS)
            pos_options_zh = [get_pos_display(pos) for pos in PART_OF_SPEECH]
            new_part_of_speech_zh = st.selectbox("词性", pos_options_zh)
            new_part_of_speech = PART_OF_SPEECH_EN[new_part_of_speech_zh]
        with col2:
            new_action = st.text_input("用法")
            new_translation = st.text_input("翻译（可选）")

        if st.button("添加"):
            if new_action:
                action_id = db.create_empty_word_action(
                    new_empty_word, new_part_of_speech, new_action, new_translation
                )
                st.success(f"添加成功，ID: {action_id}")
                st.rerun()
            else:
                st.error("用法不能为空")

elif page == "例句管理":
    st.title("例句管理")

    tab1, tab2 = st.tabs(["例句列表", "批量添加"])

    with tab1:
        # 筛选条件
        col1, col2 = st.columns(2)
        with col1:
            filter_empty_word = st.selectbox(
                "筛选虚词", [None] + EMPTY_WORDS, key="filter_word"
            )
        with col2:
            col2.markdown("<br>", unsafe_allow_html=True)
            if st.button("清除筛选"):
                filter_empty_word = None
                st.rerun()

        sentences = db.get_all_example_sentences(filter_empty_word)
        st.markdown(f"### 共 {len(sentences)} 个例句")

        for sentence in sentences:
            with st.expander(f"{sentence['sentence'][:50]}..."):
                st.markdown(f"**例句**: {sentence['sentence']}")
                st.markdown(f"**虚词**: {sentence['empty_word']}")
                if sentence["actions"]:
                    st.markdown(f"**用法**: {', '.join(sentence['actions'])}")
                if sentence["tags"]:
                    st.markdown(f"**标签**: {sentence['tags']}")

                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("删除", key=f"del_s_{sentence['id']}"):
                        db.delete_example_sentence(sentence["id"])
                        st.success("已删除")
                        st.rerun()

    with tab2:
        st.markdown("### 批量添加例句")

        sentence_input = st.text_area(
            "输入例句（每行一句）",
            height=200,
            placeholder="例如：\n蟹六跪而二螯\n青，取之于蓝，而青于蓝",
        )

        if st.button("自动识别并添加"):
            if sentence_input:
                lines = [
                    line.strip() for line in sentence_input.split("\n") if line.strip()
                ]
                added_count = 0

                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, line in enumerate(lines):
                    # 检测虚词
                    empty_words = db.detect_empty_words_in_sentence(line)

                    if empty_words:
                        # 为每个虚词查找可用的用法
                        for empty_word in empty_words:
                            actions = db.get_all_empty_word_actions(empty_word)
                            if actions:
                                # 默认选择第一个用法
                                action_id = actions[0]["id"]
                                tags = [f"batch_{datetime.now().strftime('%Y%m%d')}"]

                                try:
                                    db.create_example_sentence(
                                        line, tags, empty_word, [action_id]
                                    )
                                    added_count += 1
                                except Exception as e:
                                    st.warning(f"添加失败: {line} - {str(e)}")

                    progress_bar.progress((i + 1) / len(lines))
                    status_text.text(f"处理中: {i + 1}/{len(lines)}")

                progress_bar.empty()
                status_text.empty()

                st.success(f"成功添加 {added_count} 个例句")
            else:
                st.error("请输入例句")

        st.markdown("### 手动添加单句")

        col1, col2 = st.columns(2)
        with col1:
            manual_sentence = st.text_input("例句")
            manual_tags = st.text_input(
                "标签（用逗号分隔）", placeholder="例如: 常见,重要"
            )
        with col2:
            manual_empty_word = st.selectbox("虚词", EMPTY_WORDS)
            manual_actions = db.get_all_empty_word_actions(manual_empty_word)

            if manual_actions:
                manual_action_ids = st.multiselect(
                    "选择用法",
                    manual_actions,
                    format_func=lambda x: f"{x['action']} ({get_pos_display(x['part_of_speech'])})",
                    key="manual_actions",
                )

        if st.button("添加单句"):
            if manual_sentence and manual_action_ids:
                tags = (
                    [tag.strip() for tag in manual_tags.split(",") if tag.strip()]
                    if manual_tags
                    else []
                )
                action_ids = [a["id"] for a in manual_action_ids]

                db.create_example_sentence(
                    manual_sentence, tags, manual_empty_word, action_ids
                )
                st.success("添加成功")
                st.rerun()
            else:
                st.error("请填写完整信息")

elif page == "试卷生成":
    st.title("生成试卷")

    # 筛选条件
    st.markdown("### 筛选条件")

    col1, col2 = st.columns(2)
    with col1:
        # 添加全选选项
        all_words_plus = ["全选"] + EMPTY_WORDS
        filter_empty_words_selected = st.multiselect(
            "虚词", all_words_plus, key="filter_words_gen"
        )

        # 处理全选逻辑
        if "全选" in filter_empty_words_selected:
            filter_empty_words = EMPTY_WORDS
        else:
            filter_empty_words = filter_empty_words_selected

        # 获取所有可能的词性
        all_pos = set()
        if filter_empty_words:
            actions = db.get_all_empty_word_actions()
            for action in actions:
                if action["empty_word"] in filter_empty_words:
                    all_pos.add(action["part_of_speech"])

        # 显示中文词性供选择
        pos_display_options = ["全选"] + sorted(
            [get_pos_display(pos) for pos in all_pos]
        )
        filter_pos_zh = st.multiselect("词性", pos_display_options, key="filter_pos")

        # 处理词性全选逻辑
        if "全选" in filter_pos_zh and filter_pos_zh:
            # 选择了全选
            pos_display_options_filtered = [
                p for p in pos_display_options if p != "全选"
            ]
            filter_pos = [
                PART_OF_SPEECH_EN[pos_zh] for pos_zh in pos_display_options_filtered
            ]
        else:
            # 转换为英文用于查询
            filter_pos = (
                [PART_OF_SPEECH_EN[pos_zh] for pos_zh in filter_pos_zh]
                if filter_pos_zh
                else []
            )

    with col2:
        question_count = st.number_input("题目数量", min_value=1, value=10, step=1)
        paper_title = st.text_input(
            "试卷标题", value=f"虚词练习 {datetime.now().strftime('%Y-%m-%d')}"
        )

    if st.button("生成试卷", type="primary"):
        if question_count > 0:
            # 获取符合条件的例句
            sentences = db.get_all_example_sentences()

            # 过滤例句
            filtered_sentences = []
            for sentence in sentences:
                if (
                    filter_empty_words
                    and sentence["empty_word"] not in filter_empty_words
                ):
                    continue

                # 检查词性
                if filter_pos:
                    sentence_actions = db.get_all_empty_word_actions(
                        sentence["empty_word"]
                    )
                    if not any(
                        action["part_of_speech"] in filter_pos
                        for action in sentence_actions
                    ):
                        continue

                filtered_sentences.append(sentence)

            if len(filtered_sentences) == 0:
                st.error("没有符合条件的例句")
            else:
                # 随机打乱例句顺序（不按数据库顺序）
                random.shuffle(filtered_sentences)

                # 随机选择例句
                selected_sentences = random.sample(
                    filtered_sentences, min(question_count, len(filtered_sentences))
                )

                # 为每个句子生成题目
                questions = []
                for sentence in selected_sentences:
                    # 获取正确答案
                    correct_action_id = (
                        sentence.get("action_ids", [0])[0]
                        if sentence.get("action_ids")
                        else None
                    )

                    if correct_action_id:
                        # 获取3个干扰项（同一个虚词的其他用法）
                        all_actions = db.get_all_empty_word_actions(
                            sentence["empty_word"]
                        )
                        wrong_actions = [
                            a for a in all_actions if a["id"] != correct_action_id
                        ]
                        options = random.sample(
                            wrong_actions, min(3, len(wrong_actions))
                        )

                        # 添加正确答案
                        correct_option = next(
                            (a for a in all_actions if a["id"] == correct_action_id),
                            None,
                        )
                        if correct_option:
                            options.append(correct_option)
                            random.shuffle(options)

                        questions.append(
                            {
                                "sentence_id": sentence["id"],
                                "action_id": correct_action_id,
                                "options": [
                                    {
                                        "action_id": a["id"],
                                        "is_correct": a["id"] == correct_action_id,
                                    }
                                    for a in options
                                ],
                            }
                        )

                # 创建试卷
                paper_id = db.create_paper(paper_title, questions)
                st.success(f"试卷创建成功！ID: {paper_id}")
                st.rerun()
        else:
            st.error("题目数量必须大于0")

else:  # 试卷列表
    st.title("试卷列表")

    papers = db.get_all_papers()

    if not papers:
        st.info("还没有试卷")
    else:
        for paper in papers:
            with st.expander(f"{paper['title']} - {paper['created_at']}"):
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(f"**标题**: {paper['title']}")
                    st.markdown(f"**题目数**: {paper['question_count']}")
                    st.markdown(f"**创建时间**: {paper['created_at']}")

                with col2:
                    if st.button("查看详情", key=f"view_{paper['id']}"):
                        st.session_state[f"view_paper_id"] = paper["id"]
                        st.rerun()

                with col3:
                    if st.button("删除", key=f"del_p_{paper['id']}"):
                        db.delete_paper(paper["id"])
                        st.success("已删除")
                        st.rerun()

        # 查看试卷详情
        if f"view_paper_id" in st.session_state:
            paper_id = st.session_state["view_paper_id"]
            paper = db.get_paper(paper_id)

            st.markdown("---")
            st.markdown(f"## 试卷: {paper['title']}")

            # 导出选项
            st.markdown("### 导出选项")
            col1, col2, col3 = st.columns(3)
            with col1:
                show_options = st.checkbox("显示选项", value=False)
            with col2:
                show_answer = st.checkbox("显示答案", value=False)
            with col3:
                highlight_word = st.checkbox("高亮虚词", value=False)

            # 导出按钮
            import io

            # 检查是否已经生成文档
            doc_ready_key = f"doc_ready_{paper_id}"

            if st.button("导出为 Word", key=f"export_btn_{paper_id}"):
                # 生成文档
                doc = Document()

                # 标题
                title = doc.add_heading(paper["title"], 0)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER

                # 添加空行
                doc.add_paragraph()

                # 题目
                for i, question_data in enumerate(paper["questions"], 1):
                    # 获取句子
                    sentence = question_data.get("sentence", "")
                    action_id = question_data.get("action_id")

                    # 题号
                    para = doc.add_paragraph(f"{i}. ", style="Normal")

                    # 高亮虚词
                    if highlight_word and sentence:
                        # 找到虚词
                        empty_word = None
                        for word in EMPTY_WORDS:
                            if word in sentence:
                                empty_word = word
                                break

                        if empty_word:
                            # 找到虚词在句子中的位置
                            parts = sentence.split(empty_word, 1)
                            if parts[0]:
                                para.add_run(parts[0])
                            run = para.add_run(empty_word)
                            run.bold = True
                            if len(parts) > 1 and parts[1]:
                                para.add_run(parts[1])
                        else:
                            para.add_run(sentence)
                    else:
                        if sentence:
                            para.add_run(sentence)

                    # 选项
                    if show_options and question_data.get("options"):
                        options = question_data["options"]
                        for j, option in enumerate(options, 1):
                            # 构建选项文本：作用 + 意思
                            action = option.get("action", "")
                            translation = option.get("translation", "")
                            if translation:
                                option_text = (
                                    f"{chr(96 + j)}. {action}（{translation}）"
                                )
                            else:
                                option_text = f"{chr(96 + j)}. {action}"
                            para = doc.add_paragraph(option_text)
                            para.paragraph_format.left_indent = Inches(0.5)

                    # 答案
                    if show_answer:
                        options = question_data.get("options", [])
                        correct_answer = next(
                            (opt for opt in options if opt.get("is_correct")), None
                        )
                        if correct_answer:
                            action = correct_answer.get("action", "")
                            translation = correct_answer.get("translation", "")
                            if translation:
                                answer_text = f"答案: {action}（{translation}）"
                            else:
                                answer_text = f"答案: {action}"
                            para = doc.add_paragraph(answer_text)
                            para.paragraph_format.left_indent = Inches(0.5)

                    doc.add_paragraph()  # 空行

                # 保存到内存
                filename = f"{paper['title']}.docx"
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_bytes = doc_io.getvalue()

                # 存储到 session_state
                st.session_state[f"doc_bytes_{paper_id}"] = doc_bytes
                st.session_state[f"doc_filename_{paper_id}"] = filename
                st.session_state[doc_ready_key] = True

                st.success("试卷已生成！")
                st.rerun()

            # 如果文档已生成，显示下载按钮
            if st.session_state.get(doc_ready_key, False):
                doc_bytes = st.session_state.get(f"doc_bytes_{paper_id}")
                doc_filename = st.session_state.get(f"doc_filename_{paper_id}")

                if doc_bytes and doc_filename:
                    st.download_button(
                        "📥 下载试卷",
                        doc_bytes,
                        doc_filename,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"download_btn_{paper_id}",
                        use_container_width=True,
                    )

            # 显示题目预览
            st.markdown("### 题目预览")
            for i, question_data in enumerate(paper["questions"], 1):
                st.markdown(f"#### 第 {i} 题")
                st.markdown(f"**例句**: {question_data['sentence']}")

                if question_data["options"]:
                    st.markdown("**选项**:")
                    for j, option in enumerate(question_data["options"], 1):
                        # 构建选项文本：作用 + 意思
                        action = option.get("action", "")
                        translation = option.get("translation", "")
                        is_correct = option.get("is_correct", False)
                        if translation:
                            option_text = f"{chr(96 + j)}. {action}（{translation}）"
                        else:
                            option_text = f"{chr(96 + j)}. {action}"

                        # 添加正确答案标记
                        if is_correct:
                            option_text += " ✓"

                        st.markdown(option_text)
