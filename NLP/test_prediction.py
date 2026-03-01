def should_trade(sentiment, confidence, market_price):
    # sentiment: -1 to +1
    # confidence: 0 to 1
    # market_price: 0 to 1 (current YES price)
    
    signal_strength = abs(sentiment) * confidence
    
    if signal_strength < 0.5:  # not strong enough
        return None
    
    my_probability = (sentiment + 1) / 2  # convert -1→+1 to 0→1
    edge = my_probability - market_price
    
    if edge > 0.10:
        return "buy_yes"
    elif edge < -0.10:
        return "buy_no"
    else:
        return None