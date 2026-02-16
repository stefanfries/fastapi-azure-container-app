# Specification of Business Requirements

The objective of this project is to develop an API which is able to fetch various type of financial informations from a publically available website. In the first stage of development the comdirect website is used as the only source of information. In later stages it shoukld be possible to add other datasources if required.

The API will be used to feed other software modules with all the data required for financial analysis. To do so the most important endpoints to be developed are:

 - /basedata: returns base information of a financial instruments which are ficed and do not change over time. Examples are instrument name (perhaps short and long name), WKN, ISIN, Symbol, asset class (incl subclass if available), trading venues and internal trading venue id´s.
 - basedata should be persisted to reduce scraping of the comdirect webpage to a minimum
 - /pricedata: returns the current price of a specific instrument at a given trading venue (ask and bid prices if available), currency, timestamp, asset class
 - /history: returns historic financial data (open, high, low, close, volume) for a given instrument at a given trading venue for a given time period in given intervals

 The API supports all major asset classes like stocks, warants, fonds, etfs, certificates, bonds, indices, commodities, and currencies.

test_warrants = ['MA5GEG', 'MA59PF', 'MC9UZT', 'MA7QYE', 'MA9RMH', 'MA6P6Z', 'MA5UK0', 'MA4R9G', 'SF41HU', 'SF5RSR', \
                   'MA9RH9', 'BASF11', '906866', 'HAFX6Q', 'A0MW0M', 'A0YEDL', 'PH6USA', 'MC02EM']
test_indizes = ['846900', '846741', '720327', '965338', '965814', 'A0AE1X', '969420', '965814']

test_bonds = ['450900', 'A0AUXK', '353254', '128531', 'A0T6UH', 'A0BCJ2']

test_etfs = ['A1C79N', 'A1C79W', 'A2DWM4']

test_commodities = ['965515', '965310']

test_currencies = ['965275', 'A0C32V', '965308']

depot_mega_trend= ['JK2M14', 'MB76DR', 'JK3WZ0', 'ME2CU8', 'MJ1278', 'JL8R2L', 'JV8872']

depot_test_fonds = ['A0F4Y2', 'A0NEBA', '921826', '980701']

depot_certificates = ['PD3W5U', 'MB2BY3', 'PH9PEC', 'SH8ARB', 'PD4A1M', 'MS8JN4', 'SR65CB', 'MB3B7G', 'SR5DBJ']

Instruments from all asset classes share a common set of attributes: name, WKN, ISIN, trading venue and id_notation, currency. But additionally each asset class has a number of characteristics specific for the asset class ("Aktieninformationen" or "Stammdaten")
