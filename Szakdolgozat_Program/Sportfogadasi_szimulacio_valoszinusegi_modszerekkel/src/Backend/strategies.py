def flat_betting(bets, stake, bankroll=1000):
    bankroll = [bankroll]
    for bet in bets:
        if bet['won']:
            bankroll.append(bankroll[-1] + stake * (bet['odds'] - 1))
        else:
            bankroll.append(bankroll[-1] - stake)
    return bankroll

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

def fibonacci(bets, base_stake):
    bankroll = [1000]
    fib_sequence = [base_stake, base_stake]
    idx = 0
    for bet in bets:
        if bet['won']:
            bankroll.append(bankroll[-1] + fib_sequence[idx] * (bet['odds'] - 1))
            idx = max(idx - 2, 0)
        else:
            bankroll.append(bankroll[-1] - fib_sequence[idx])
            idx += 1
            if idx >= len(fib_sequence):
                fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return bankroll

def kelly_criterion(bets, bankroll_start=1000):
    bankroll = [bankroll_start]
    for bet in bets:
        b = bet['odds'] - 1
        p = bet['model_probability']
        q = 1 - p

        # 💥 Védelem a 0-val való osztás ellen
        if b <= 0:
            bankroll.append(bankroll[-1])
            continue

        stake_fraction = (b * p - q) / b

        # ❗Ha negatív a Kelly stake, akkor nem fogadunk
        if stake_fraction <= 0:
            bankroll.append(bankroll[-1])
            continue

        stake = bankroll[-1] * stake_fraction

        if bet['won']:
            bankroll.append(bankroll[-1] + stake * b)
        else:
            bankroll.append(bankroll[-1] - stake)

    return bankroll


