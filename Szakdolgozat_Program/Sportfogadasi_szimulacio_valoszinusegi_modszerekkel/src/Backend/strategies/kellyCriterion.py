def kelly_criterion(bets, bankroll_start=1000, fractional=0.25, min_stake=10):
    current_bankroll = bankroll_start
    bankrolls = [current_bankroll]
    stakes_used = []

    for bet in bets:
        b = float(bet['odds']) - 1
        p = float(bet['model_probability']) / 100.0  # Százalékból valószínűség (pl. 43.66 -> 0.4366)
        q = 1 - p

        if b <= 0:
            stakes_used.append(0)
            bankrolls.append(current_bankroll)
            continue

        stake_fraction = (b * p - q) / b

        if stake_fraction <= 0:
            stakes_used.append(0)
            bankrolls.append(current_bankroll)
            continue

        # Fractional Kelly alkalmazása a kockázat csökkentésére
        stake_fraction *= fractional

        stake = current_bankroll * stake_fraction

        # Minimum tét alkalmazása, ha a kalkulált tét túl alacsony
        if stake < min_stake and current_bankroll >= min_stake:
            stake = min_stake

        # Bankroll kontroll: van-e elég pénz?
        if current_bankroll < stake:
            stake = current_bankroll  # Legfeljebb a teljes bankrollt tesszük meg

        stakes_used.append(stake)

        if bet['won']:
            # Teljes kifizetés = eredeti tét + nyereség
            payout = stake * bet['odds']  # Nem csak a nyereség (b*stake), hanem a teljes kifizetés
            current_bankroll = current_bankroll - stake + payout  # Levontuk a tétet, majd hozzáadtuk a kifizetést
        else:
            current_bankroll -= stake

        bankrolls.append(current_bankroll)

    return bankrolls, stakes_used