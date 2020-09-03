##############################################################################
# Copyright (C) 2018, 2019, 2020 Dominic O'Kane
##############################################################################

from scipy import optimize


from ...finutils.FinDate import FinDate
from ...finutils.FinError import FinError
from ...finutils.FinFrequency import FinFrequency, FinFrequencyTypes
from ...finutils.FinDayCount import FinDayCount, FinDayCountTypes
from ...finutils.FinSchedule import FinSchedule
from ...finutils.FinCalendar import FinCalendarTypes
from ...finutils.FinCalendar import FinBusDayAdjustTypes
from ...finutils.FinCalendar import FinDateGenRuleTypes
from ...finutils.FinHelperFunctions import labelToString, checkArgumentTypes
from ...market.curves.FinDiscountCurve import FinDiscountCurve

###############################################################################
# TODO: Need to complete and verify the risk sensitivity calculations.
###############################################################################

###############################################################################


def _f(dm, *args):
    ''' Function used to do solve root search in DM calculation '''

    self = args[0]
    settlementDate = args[1]
    nextCoupon = args[2]
    currentLibor = args[3]
    futureLibor = args[4]
    fullPrice = args[5]

    px = self.fullPriceFromDiscountMargin(settlementDate,
                                          nextCoupon,
                                          currentLibor,
                                          futureLibor,
                                          dm)

    objFn = px - fullPrice
    return objFn

###############################################################################


class FinBondFRN(object):
    ''' Class for managing floating rate notes that pay a floating index plus a
    quoted margin.'''

    def __init__(self,
                 maturityDate: FinDate,
                 quotedMargin: float,
                 frequencyType: FinFrequencyTypes,
                 accrualType: FinDayCountTypes,
                 faceAmount: float = 100.0):
        ''' Create FinFloatingRateNote object given its maturity date, its
        quoted margin, coupon frequency, accrual type. Face is the size of
        the position and par is the notional on which price is quoted. '''

        checkArgumentTypes(self.__init__, locals())

        self._maturityDate = maturityDate
        self._quotedMargin = quotedMargin
        self._frequencyType = frequencyType
        self._accrualType = accrualType
        self._flowDates = []
        self._frequency = FinFrequency(frequencyType)
        self._faceAmount = faceAmount   # This is the position size
        self._par = 100.0   # This is how price is quoted

        ''' I do not determine cashflow dates as I do not want to require
        users to supply the issue date and without that I do not know how
        far to go back in the cashflow date schedule. '''

        self._settlementDate = FinDate(1900, 1, 1)
        self._accruedInterest = 0.0
        self._accruedDays = 0.0

###############################################################################

    def _calculateFlowDates(self,
                            settlementDate: FinDate):
        ''' Determine the bond cashflow payment dates. '''

        # No need to generate flows if settlement date has not changed
        if settlementDate == self._settlementDate:
            return

        self._settlementDate = settlementDate
        calendarType = FinCalendarTypes.NONE
        busDayRuleType = FinBusDayAdjustTypes.NONE
        dateGenRuleType = FinDateGenRuleTypes.BACKWARD

        self._flowDates = FinSchedule(settlementDate,
                                      self._maturityDate,
                                      self._frequencyType,
                                      calendarType,
                                      busDayRuleType,
                                      dateGenRuleType)._generate()

        self._pcd = self._flowDates[0]
        self._ncd = self._flowDates[1]

###############################################################################

    def fullPriceFromDiscountMargin(self,
                                    settlementDate: FinDate,
                                    resetLibor: float,
                                    currentLibor: float,
                                    futureLibor: float,
                                    dm: float):
        ''' Calculate the full price of the bond from its discount margin and
        making assumptions about the future Libor rates. '''

        self._calculateFlowDates(settlementDate)
        self.calcAccruedInterest(settlementDate, resetLibor)

        dc = self._ncd - settlementDate
        dbc = self._ncd - self._pcd

        alpha = float(dc) / float(dbc)
        f = self._frequency
        q = self._quotedMargin
        y = futureLibor + dm
        c = futureLibor + q
        numFlows = len(self._flowDates)

        nextCoupon = resetLibor + self._quotedMargin
        df = pow(1.0 + (currentLibor + dm)/f, -alpha)
        pv = (nextCoupon/f) * df

        for _ in range(2, numFlows):
            df /= (1.0 + y/f)
            pv = pv + (c/f) * df

        pv += df
        pv = pv * self._par

        return pv

###############################################################################

    def principal(self,
                  settlementDate: FinDate,
                  resetLibor: float,
                  currentLibor: float,
                  futureLibor: float,
                  dm: float):
        ''' Calculate the clean trade price of the bond based on the face
        amount from its discount margin and making assumptions about the
        future Libor rates. '''

        fullPrice = self.fullPriceFromDiscountMargin(settlementDate,
                                                     resetLibor,
                                                     currentLibor,
                                                     futureLibor,
                                                     dm)

        accrued = self._accruedInterest
        principal = fullPrice * self._faceAmount / self._par - accrued
        return principal

###############################################################################

    def dollarRateDuration(self,
                           settlementDate: FinDate,
                           resetLibor: float,
                           currentLibor: float,
                           futureLibor: float,
                           dm: float):
        ''' Calculate the risk or dP/dy of the bond by bumping. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        self._calculateFlowDates(settlementDate)
        self.calcAccruedInterest(settlementDate, resetLibor)
        dy = 0.0001

        p0 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor + dy,
                                              futureLibor,
                                              dm)

        p2 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm)

        durn = (p2 - p0) / dy
        return durn

###############################################################################

    def dollarCreditDuration(self,
                             settlementDate: FinDate,
                             resetLibor: float,
                             currentLibor: float,
                             futureLibor: float,
                             dm: float):
        ''' Calculate the risk or dP/dy of the bond by bumping. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        self._calculateFlowDates(settlementDate)
        self.calcAccruedInterest(settlementDate, resetLibor)
        dy = 0.0001

        p0 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm + dy)

        p2 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm)

        durn = (p2 - p0) / dy
        return durn

###############################################################################

    def macauleyRateDuration(self,
                             settlementDate: FinDate,
                             resetLibor: float,
                             currentLibor: float,
                             futureLibor: float,
                             dm: float):
        ''' Calculate the Macauley duration of the FRN on a settlement date
        given its yield to maturity. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        dd = self.dollarRateDuration(settlementDate,
                                     resetLibor,
                                     currentLibor,
                                     futureLibor,
                                     dm)

        fp = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm)

        md = dd * (1.0 + (resetLibor + dm) / self._frequency) / fp
        return md

###############################################################################

    def modifiedRateDuration(self,
                             settlementDate: FinDate,
                             resetLibor: float,
                             currentLibor: float,
                             futureLibor: float,
                             dm: float):
        ''' Calculate the modified duration of the bondon a settlement date
        given its yield to maturity. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        dd = self.dollarRateDuration(settlementDate,
                                     resetLibor,
                                     currentLibor,
                                     futureLibor,
                                     dm)

        fp = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm)
        md = dd / fp
        return md

###############################################################################

    def modifiedCreditDuration(self,
                               settlementDate: FinDate,
                               resetLibor: float,
                               currentLibor: float,
                               futureLibor: float,
                               dm: float):
        ''' Calculate the modified duration of the bondon a settlement date
        given its yield to maturity. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        dd = self.dollarCreditDuration(settlementDate,
                                       resetLibor,
                                       currentLibor,
                                       futureLibor,
                                       dm)

        fp = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm)
        md = dd / fp
        return md

###############################################################################

    def convexityFromDiscountMargin(self,
                                    settlementDate: FinDate,
                                    resetLibor: float,
                                    currentLibor: float,
                                    futureLibor: float,
                                    dm: float):
        ''' Calculate the bond convexity from the discount margin using a
        numerical bump of size 1 basis point and taking second differences. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        self._calculateFlowDates(settlementDate)
        self.calcAccruedInterest(settlementDate, resetLibor)

        dy = 0.0001

        p0 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor - dy,
                                              futureLibor,
                                              dm)

        p1 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor,
                                              futureLibor,
                                              dm)

        p2 = self.fullPriceFromDiscountMargin(settlementDate,
                                              resetLibor,
                                              currentLibor + dy,
                                              futureLibor,
                                              dm)

        print("The Value output has not been confirmed")
        conv = ((p2 + p0) - 2.0 * p1) / dy / dy / p1 / self._par
        return conv

###############################################################################

    def cleanPriceFromDiscountMargin(self,
                                     settlementDate: FinDate,
                                     resetLibor: float,
                                     currentLibor: float,
                                     futureLibor: float,
                                     dm: float):
        ''' Calculate the bond clean price from the yield. '''

        if dm > 10.0:
            raise FinError("Discount margin exceeds 100000bp")

        fullPrice = self.fullPriceFromDiscountMargin(settlementDate,
                                                     resetLibor,
                                                     currentLibor,
                                                     futureLibor,
                                                     dm)

        accrued = self._accruedInterest(settlementDate, resetLibor)
        accrued = accrued * self._par / self._faceAmount

        cleanPrice = fullPrice - accrued
        return cleanPrice

###############################################################################

    def fullPriceFromDiscountCurve(self,
                                   settlementDate: FinDate,
                                   indexCurve: FinDiscountCurve,
                                   discountCurve: FinDiscountCurve):
        ''' Calculate the bond price using some discount curve to present-value
        the bond's cashflows. THIS IS NOT COMPLETE. '''
        self._calculateFlowDates(settlementDate)

        pv = 0.0

        for dt in self._flowDates:
            df = discountCurve.df(dt)
            flow = self._coupon / self._frequency
            pv = pv + flow * df

        pv = pv + df
        return pv * self._faceAmount

###############################################################################

    def discountMargin(self,
                       settlementDate: FinDate,
                       resetLibor: float,
                       currentLibor: float,
                       futureLibor: float,
                       cleanPrice: float):
        ''' Calculate the bond's yield to maturity by solving the price
        yield relationship using a one-dimensional root solver. '''
        self._calculateFlowDates(settlementDate)
        self.calcAccruedInterest(settlementDate, resetLibor)

        # Needs to be adjusted to par notional
        accrued = self._accruedInterest * self._par / self._faceAmount

        fullPrice = cleanPrice + accrued

        argtuple = (self, settlementDate, resetLibor, currentLibor,
                    futureLibor, fullPrice)

        dm = optimize.newton(_f,
                             x0=0.01,  # initial value of 10%
                             fprime=None,
                             args=argtuple,
                             tol=1e-8,
                             maxiter=50,
                             fprime2=None)
        return dm

###############################################################################

    def calcAccruedInterest(self,
                            settlementDate: FinDate,
                            resetLibor: float):
        ''' Calculate the amount of coupon that has accrued between the
        previous coupon date and the settlement date. '''

        self._calculateFlowDates(settlementDate)

        if len(self._flowDates) == 0:
            raise FinError("Accrued interest - not enough flow dates.")

        dc = FinDayCount(self._accrualType)

        if self._accrualType == FinDayCountTypes.ACT_ACT_ICMA:

            (accFactor, num, _) = dc.yearFrac(self._pcd,
                                              settlementDate,
                                              self._ncd)

            self._alpha = 1.0 - accFactor * self._frequency

        else:

            (accFactor, num, _) = dc.yearFrac(self._pcd,
                                              settlementDate)

            self._alpha = 1.0 - accFactor * self._frequency

        nextCoupon = resetLibor + self._quotedMargin
 
        self._accruedInterest = accFactor * self._faceAmount * nextCoupon
        self._accruedDays = num
        return self._accruedInterest

###############################################################################

    def printFlows(self,
                   settlementDate: FinDate):
        ''' Print a list of the unadjusted coupon payment dates used in
        analytic calculations for the bond. '''
        self._calculateFlowDates(settlementDate)
        for dt in self._flowDates[1:-1]:
            print(dt)

        print(self._flowDates[-1])

###############################################################################

    def __repr__(self):
        ''' Print a list of the unadjusted coupon payment dates used in
        analytic calculations for the bond. '''
        s = labelToString("OBJECT TYPE", type(self).__name__)
        s += labelToString("MATURITY DATE", self._maturityDate)
        s += labelToString("QUOTED MARGIN", self._quotedMargin)
        s += labelToString("FREQUENCY", self._frequencyType)
        s += labelToString("ACCRUAL TYPE", self._accrualType)
        s += labelToString("FACE AMOUNT", self._faceAmount)
        return s

###############################################################################

    def _print(self):
        ''' Simple print function for backward compatibility. '''
        print(self)

###############################################################################
