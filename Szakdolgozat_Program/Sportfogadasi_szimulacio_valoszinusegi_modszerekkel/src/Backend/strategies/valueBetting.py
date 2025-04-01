def value_betting(bets, stake):
    bankroll = [1000]
    stakes_used = []

    for bet in bets:
        model_prob = bet['model_probability']
        bookmaker_prob = 1 / bet['odds']

        if model_prob > bookmaker_prob:
            stakes_used.append(stake)
            if bet['won']:
                bankroll.append(bankroll[-1] + stake * (bet['odds'] - 1))
            else:
                bankroll.append(bankroll[-1] - stake)
        else:
            stakes_used.append(0)  # Nem tettél tétet
            bankroll.append(bankroll[-1])

    return bankroll, stakes_used
