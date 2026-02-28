import modal
import time

APP_NAME = "finnews-sentiment"
FUNCTION_NAME = "score-article"

def run_test():
    print(f"--- Connecting to Modal Function: {FUNCTION_NAME} ---")
    
    try:
        score_article = modal.Function.from_name(APP_NAME, FUNCTION_NAME)
    except Exception as e:
        print(f"Could not find function: {e}")
        return

    news_feed = [
        "Goldman Sachs predicts a 20% surge in tech stocks by year-end.",
        "Unexpected inflation spike leads to emergency rate hike rumors.",
        "Consumer spending remains flat despite holiday sales push.",
        "Breaking: Major bank reports record-breaking quarterly profits."
    ]

    print(f"Sending headlines to GPU...\n")

    for headline in news_feed:
        start_time = time.perf_counter()
        
        try:
            result = score_article.remote(headline)
            
            label = result['label'].upper()
            confidence = result['score']
            
            latency = (time.perf_counter() - start_time) * 1000

            status_icon = "🟢" if label == "POSITIVE" else "🔴" if label == "NEGATIVE" else "⚪"
            
            print(f"{status_icon} {label} | Conf: {confidence:.2%} | Latency: {latency:.2f}ms")
            print(f"   Headline: {headline}\n")

        except Exception as e:
            print(f"Error processing '{headline[:30]}...': {e}")

if __name__ == "__main__":
    run_test()