const Gdax = require('gdax');
var _ = require('underscore');
const BigNumber = require('bignumber.js');

// Parameters
var maxEntryCount = 3
var maxVolumeCount = Infinity
var pairs = ['BCH/BTC', 'BTC/EUR', 'LTC/EUR', 'BTC/USD', 'BTC/EUR', 'ETH/USD',
'ETH/EUR', 'BCH/EUR', 'ETH/BTC', 'BCH/USD']

const publicClient = new Gdax.PublicClient();
const orderbookSync = new Gdax.OrderbookSync(pairs.map(x => x.replace('/','-')));
var asksConsolidated_old = new Array()
var bidsConsolidated_old = new Array()

var kafka = require('kafka-node'),
    HighLevelProducer = kafka.HighLevelProducer,
    client = new kafka.KafkaClient({kafkaHost: "kafka.cryptoindex.me:9092"}),
    producer = new HighLevelProducer(client);

// producer.on('ready', function () {
//     console.log("Kafka producer is ready");
//     // producerReady = true;
// });
      
// producer.on('error', function (err) {
//   console.error("Problem with producing to Kafka " + err);
// })

function getConsolidatedOrderbook(entries) {
    var orderbook = new Array()
    var price = entries[0].price
    var size = new BigNumber(0)    
    var sizeAccumulator = 0
    for (var i = 0; i < entries.length; i++) {

        if (entries[i].price.isEqualTo(price)) {
            size = size.plus(entries[i].size)
        }
        else {
            orderbook.push([price, size])
            sizeAccumulator += size.toNumber()
            if (orderbook.length >= maxEntryCount || sizeAccumulator >= maxVolumeCount) {
                return orderbook
            }
            price = entries[i].price
            size = entries[i].size
        }
    }
}

var messageHandler = function (data) {
    try {

        if (_.isUndefined(data.product_id)) {
            return
        }
        orderbookState = orderbookSync.books[data.product_id].state()
        if (orderbookState.asks.length == 0 || orderbookState.bids.length == 0) {
            return
        }

        asksConsolidated = getConsolidatedOrderbook(orderbookState.asks)
        bidsConsolidated = getConsolidatedOrderbook(orderbookState.bids)

        if (!_.isEqual(asksConsolidated, asksConsolidated_old) || !_.isEqual(bidsConsolidated, bidsConsolidated_old)) {
            var delay = new Date().getTime() - (new Date(data.time).getTime());
            var symbol = data.product_id.replace("-", "/")

            var payload = {
                "exchange": "coinbasepro",
                "symbol": symbol,
                "data": {
                    "asks": asksConsolidated.map(x => [x[0].toNumber(),x[1].toNumber()]),
                    "bids": bidsConsolidated.map(x => [x[0].toNumber(),x[1].toNumber()])
                },
                "timestamp": new Date(data.time).getTime()
            };
                payloads = [
                    { topic: "orderbook", messages: JSON.stringify(JSON.stringify(payload)) },
                ];
                producer.send(payloads, function (err, data) {
                    if (err) throw err;
                    console.log(data);
                });

            console.log(data.product_id + " asks:" + asksConsolidated.toString() + ", bids:" + bidsConsolidated.toString() + " delay:" + delay.toString() + "ms");

            asksConsolidated_old = asksConsolidated
            bidsConsolidated_old = bidsConsolidated
        }
    }
    catch (err) {
        console.log('error: ' + err)
    }
}

orderbookSync.on('message', data => { messageHandler(data) })
orderbookSync.on('error', err => { console.log(err) });