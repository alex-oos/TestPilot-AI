#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    @Author :Alex
#
#              _____               ______
#     ____====  ]OO|_n_n__][.      |    |]
#    [________]_|__|________)<     
#     oo    oo  'oo OOOO-| oo\_   ~o~~~o~'
# +--+--+--+--+--+--+--+--+--+--+--+--+--+
#    @Time : 2026/3/30 16:42
#    @FIle： Knowledge_base_demo.py
#    @Software: PyCharm
"""
本地知识库搜索 Demo
依赖安装: pip install chromadb sentence-transformers
"""

import chromadb
from sentence_transformers import SentenceTransformer

# ============================================================
# 1. 初始化：加载 Embedding 模型 + 创建本地数据库
# ============================================================

print("正在加载 Embedding 模型...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")  # 支持中文

# 创建本地持久化数据库（数据保存在 ./chroma_db 目录）
client = chromadb.PersistentClient(path="./chroma_db")

# 获取或创建一个集合（类似表）
collection = client.get_or_create_collection(name="my_knowledge_base")


# ============================================================
# 2. 添加文档到知识库
# ============================================================

def add_documents(docs: list[dict]):
    """
    docs 格式: [{"id": "1", "text": "内容", "metadata": {...}}]
    """
    texts = [d["text"] for d in docs]
    ids = [d["id"] for d in docs]
    metadatas = [d.get("metadata", {}) for d in docs]

    # 生成向量
    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"✅ 已添加 {len(docs)} 条文档")


# ============================================================
# 3. 搜索知识库
# ============================================================

def search(query: str, top_k: int = 3):
    """
    输入问题，返回最相关的 top_k 条文档
    """
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    print(f"\n🔍 查询: {query}")
    print("-" * 40)
    for i, (doc, score) in enumerate(zip(results["documents"][0], results["distances"][0])):
        metadata = results["metadatas"][0][i]
        # ChromaDB 返回的是 L2 距离，越小越相关
        similarity = round(1 - score / 2, 4)  # 转换为相似度（仅供参考）
        print(f"[{i+1}] 相似度: {similarity:.4f}")
        print(f"    内容: {doc}")
        if metadata:
            print(f"    来源: {metadata}")
        print()

    return results


# ============================================================
# 4. 示例运行
# ============================================================

if __name__ == "__main__":

    # --- 示例文档（替换成你自己的内容）---
    sample_docs = [
        {"id": "1", "text": "Python 是一种高级编程语言，以简洁易读著称，广泛用于数据科学和 Web 开发。", "metadata": {"source": "编程介绍"}},
        {"id": "2", "text": "ChromaDB 是一个开源的向量数据库，专为 AI 应用设计，支持本地和云端部署。", "metadata": {"source": "数据库文档"}},
        {"id": "3", "text": "机器学习是人工智能的一个子领域，通过数据训练模型来进行预测和决策。", "metadata": {"source": "AI 教程"}},
        {"id": "4", "text": "RAG（检索增强生成）是一种将知识库检索与大语言模型结合的技术架构。", "metadata": {"source": "AI 架构"}},
        {"id": "5", "text": "向量数据库通过存储高维向量，支持语义相似度搜索，与传统关键词搜索不同。", "metadata": {"source": "数据库原理"}},
    ]

    # 检查是否已有数据，避免重复添加
    if collection.count() == 0:
        print("📚 初始化知识库，添加示例文档...")
        add_documents(sample_docs)
    else:
        print(f"📚 知识库已有 {collection.count()} 条文档")

    # --- 搜索示例 ---
    search("什么是向量数据库？")
    search("如何用 Python 做 AI？")

    # --- 交互模式 ---
    print("\n" + "=" * 40)
    print("进入交互搜索模式，输入 'exit' 退出")
    print("=" * 40)
    while True:
        query = input("\n请输入搜索内容: ").strip()
        if query.lower() == "exit":
            break
        if query:
            search(query, top_k=3)
