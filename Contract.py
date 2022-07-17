import time
import numpy as np
import requests
import json
from scipy.stats import norm
import cryptocompare
from constant import RISK_FREE_RATE
import time
from calendar import timegm

def BS_CALL(S, K, T, r, sigma):
  N = norm.cdf
  d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
  d2 = d1 - sigma * np.sqrt(T)
  return S * N(d1) - K * np.exp(-r*T)* N(d2)

def BS_PUT(S, K, T, r, sigma):
  N = norm.cdf
  d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
  d2 = d1 - sigma* np.sqrt(T)
  return K*np.exp(-r*T)*N(-d2) - S*N(-d1)


# This class is bloated because I want to keep the jupyter notebook clean and readable.
# Contract class holds the:
# contract ID, strike, expiration, years to expiration, Black Scholes price, and theoretical APY of Covered Calls strategy
# The contract does not calculate the BS price or APY on creation because they don't always need to be calculated and are computation heavy
class Contract:

  # Finds Black Scholes fair value price (currently using a hard coded I.V value)
  def findBS_Price(self):

    #TODO NOT A LEGITIMATE I.V, have to find an estimate someway, 85% is an arbitrary number
    impliedVol = 0.85

    if (self.type == "call"):
      self.BS_Price = BS_CALL(self.underlyingPrice, self.strike, self.yearsToExpiration, RISK_FREE_RATE, impliedVol)
    elif (self.type == "put"):
      self.BS_Price == BS_CALL(self.strike, self.underlyingPrice, self.yearsToExpiration, RISK_FREE_RATE, impliedVol)

    return self.BS_Price 

  # This method calculates the APY that a covered call strategy would return at the current price 
  # assuming the strategy was repeated each time the contract reached maturity
  # This is an optimistic assumption, true APY would be lower
  def findCCAPY(self):

    if (self.underlyingPrice > self.strike):
      print ("Option is already in the money, this is not a part of my covered calls strategy")
      self.APY = -1
      return self.APY
      
    # Formatting request for ticker info on the contract using the contractID
    url = "https://api.ledgerx.com/trading/contracts/" + str(self.id) + "/ticker"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    decodedTickerInfo = json.loads(response.text)

    # Contract volume traded in last 24 hours
    volume = decodedTickerInfo['data']['volume_24h']

    # If vol is not greater than 5 I will use bid ask midpoint instead b/c can't trust last price
    if (volume > 5):
      currentPrice = (decodedTickerInfo['data']['last_trade']['price']) / 100 ## to account for the extra zeroes
      print("Contract ID: ", self.id, "current price based on last price: ", currentPrice)
    else:
      currentPrice = (decodedTickerInfo['data']['ask'] - decodedTickerInfo['data']['bid']) / 200 # average and to account for extra zeroes
      print("Contract ID: ", self.id, "current price based on bid ask midpt: ", currentPrice)

    timeMultiple = 1 / self.yearsToExpiration # How many times this contract could theoretically mature per year

    returns = currentPrice * timeMultiple

    self.APY = returns / self.underlyingPrice

    return self.APY

  # CONSTRUCTOR
  def __init__(self, id, strike, expiration, type):
    self.id = id
    self.strike = strike / 100
    self.expiration = expiration
    self.yearsToExpiration = None
    self.type = type
    self.BS_Price = None
    self.underlyingPrice = None
    self.APY = None
    
    # Current underlying Eth price, could adjust if I want to expand to BTC
    jsonunderlyingPrice = cryptocompare.get_price('ETH', currency='USD', full=False)
    self.underlyingPrice = jsonunderlyingPrice['ETH']['USD']


    # calculation for the days until expiration
    currentUTCTimeUnix = time.time()

    # date formatting
    formattedExpirationDate = time.strptime(self.expiration, "%Y-%m-%d %H:%M:%S%z")
    expirationTimeUnix = timegm(formattedExpirationDate)

    timeToExpirationSeconds = expirationTimeUnix - currentUTCTimeUnix
    daysToExpiration = float (timeToExpirationSeconds / float(86400.0))
    self.yearsToExpiration = float (daysToExpiration/ 365.0)