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