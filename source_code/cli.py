import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"          
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from rag import IndustrialChatbot


def main():
    print("Loading models (first run downloads them, please wait)...")
    bot = IndustrialChatbot()
    print("\nIndustrial Chatbot ready. Type 'exit' to quit.\n")
    previous_question = None
    previous_answer = None
    while True:
        question = input("You: ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue
        answer, hits = bot.answer(
            question,
            previous_question=previous_question,
            previous_answer=previous_answer,
        )
        previous_question = question
        previous_answer = answer
        print(f"\nBot: {answer}")
        print("\nSources:")
        for h in hits:
            print(f"  - {h['source']} (chunk {h['chunk_id']}, score {h['score']:.2f})")
        print()


if __name__ == "__main__":
    main()