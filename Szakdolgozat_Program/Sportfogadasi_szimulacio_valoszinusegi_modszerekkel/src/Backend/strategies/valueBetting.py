def value_betting(bets, stake):
    bankroll = [1000]
    for bet in bets:
        model_prob = bet['model_probability']
        bookmaker_prob = 1 / bet['odds']
        if model_prob > bookmaker_prob:
            if bet['won']:
                bankroll.append(bankroll[-1] + stake * (bet['odds'] - 1))
            else:
                bankroll.append(bankroll[-1] - stake)
        else:
            bankroll.append(bankroll[-1])  # Ha nincs érték, nem fogadunk
    return bankroll