def fibonacci(bets, base_stake, bankroll_start=None):
    bankroll = [bankroll_start if bankroll_start is not None else 0]
    stakes = []
    sequence = [base_stake, base_stake]
    index = 0

    tracking_bankroll = bankroll_start is not None and bankroll_start > 0

    for bet in bets:
        current_bankroll = bankroll[-1]

        # A következő tét nagysága a Fibonacci szerint
        expected_stake = sequence[index] if index < len(sequence) else sequence[-1] + sequence[-2]

        if tracking_bankroll:
            if current_bankroll <= 0:
                stakes.append(0)
                bankroll.append(current_bankroll)
                continue

            if current_bankroll < expected_stake:
                actual_stake = current_bankroll  # A megmaradt bankrollal fogadunk
            else:
                actual_stake = expected_stake
        else:
            actual_stake = expected_stake

        win = bet['won']
        odds = bet['odds']

        stakes.append(actual_stake)

        if win:
            profit = actual_stake * (odds - 1)
            index = 0
            sequence = [base_stake, base_stake]
        else:
            profit = -actual_stake
            sequence.append(sequence[-1] + sequence[-2])
            index += 1

        bankroll.append(current_bankroll + profit)

    return bankroll, stakes
