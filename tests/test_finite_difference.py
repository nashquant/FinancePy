from pytest import approx

from financepy.models.finite_difference import black_scholes_finite_difference, PUT_CALL, AMER_EURO
from financepy.utils.global_vars import gDaysInYear

def test_black_scholes_finite_difference():
    s0 = 1
    r = 0.04
    mu = -0.03
    sigma = 0.2

    valuation_date = Date(1, 1, 2016)
    expiry_date = Date(30, 12, 2020)
    strike = 1.025
    dig = 0
    pc = PUT_CALL.CALL.value
    ea = AMER_EURO.EURO.value
    smooth = 0

    theta = 0.5
    wind = 0
    num_std = 5
    num_t = 50
    num_s = 200
    update = 0
    num_pr = 1

    # European call
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                             num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.07939664662902503)
    
    # smooth
    smooth = 1
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.07945913698961202)
    smooth = 0

    # dig
    dig = 1
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.2153451094307548)

    #smooth dig
    smooth = 1
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.22078914857802928)
    smooth = 0
    dig = 0

    # European put
    pc = PUT_CALL.PUT.value
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.2139059947533305)

    # American put
    ea = AMER_EURO.AMER.value
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.2165916613669189)

    # American call
    pc = PUT_CALL.CALL.value
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.10259475990431438)
    ea = AMER_EURO.EURO.value

    # wind=1
    wind = 1
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.07834108133101789)

    # wind=2
    wind = 2
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.08042112779963827)

    # wind=-1
    wind = -1
    _, v = black_scholes_finite_difference(s0, r, mu, sigma, expiry_date, valuation_date, strike, dig, pc, ea, smooth, theta, wind,
                                           num_std, num_t, num_s, update, num_pr)
    assert v == approx(0.08042112779963827)
    wind = 0


from financepy.market.curves.discount_curve_flat import DiscountCurveFlat
from financepy.models.black_scholes import BlackScholes
from financepy.utils.date import Date
from financepy.products.equity.equity_binomial_tree import EquityTreePayoffTypes
from financepy.products.equity.equity_binomial_tree import EquityTreeExerciseTypes
from financepy.products.equity.equity_binomial_tree import EquityBinomialTree
import numpy as np

stock_price = 50.0
risk_free_rate = 0.06
dividend_yield = 0.04
volatility = 0.40

valuation_date = Date(1, 1, 2016)
expiry_date = Date(1, 1, 2021)
model = BlackScholes(volatility)
discount_curve = DiscountCurveFlat(valuation_date, risk_free_rate)
dividend_curve = DiscountCurveFlat(valuation_date, dividend_yield)

num_steps = 100

strike_price = 50.0



def test_european_call():
    # payoff = EquityTreePayoffTypes.VANILLA_OPTION
    payoff = PUT_CALL.CALL.value
    exercise = EquityTreeExerciseTypes.EUROPEAN
    params = np.array([1.0, strike_price])

    #_, v = black_scholes_finite_difference(stock_price, risk_free_rate, mu, volatility**2, expiry, strike_price, dig,
    #                                       payoff, exercise, smooth, theta, wind,
    #                                       num_std, num_steps, num_s, update, num_pr)
    """
    value = tree.value(
        stock_price,
        discount_curve,
        dividend_curve,
        volatility,
        num_steps,
        valuation_date,
        payoff,
        expiry_date,
        payoff,
        exercise,
        params)
    """
    # assert [round(x, 4) for x in value] == [8.0175, 0.5747, 0.0187, -3.8111]  # price, delta, gamma, theta
