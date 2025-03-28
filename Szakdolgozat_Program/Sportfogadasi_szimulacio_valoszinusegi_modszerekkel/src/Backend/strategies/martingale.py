def martingale(bets, base_stake):
    bankroll = [1000]
    current_stake = base_stake
    for bet in bets:
        if bet['won']:
            bankroll.append(bankroll[-1] + current_stake * (bet['odds'] - 1))
            current_stake = base_stake
        else:
            bankroll.append(bankroll[-1] - current_stake)
            current_stake *= 2
    return bankroll