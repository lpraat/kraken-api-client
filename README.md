# kraken-api-client
Python ([REST](https://docs.kraken.com/rest/) + [Websockets](https://docs.kraken.com/websockets/)) client to interact with the Kraken Exchange (retrieve user data, perform spot trading, stake assets, and so on).

# Basic Usage

## REST Client
Note that for requests requiring authentication the client expects the *api_key* set in the KRAKEN_KEY environment variable and the *api_secret* in the KRAKEN_PK environment variable.
```python
from kraken_client.rest import RESTKrakenClient

kc = RESTKrakenClient(base_url="https://api.kraken.com")

# Check the status of the exchange
print(kc.system_status())

# Currently, the REST client exposes as methods the following endpoints:
#   - "Get System Status"
#   - "Get Account Balance"
#   - "Get Websockets Token"
# For other endpoints you can use the custom_request method:
# e.g., for the "Add Order"
print(kc.custom_auth_request(  # use custom_request for non-authenticated requests
    endpoint="https://api.kraken.com/0/private/AddOrder",
    method='POST',
    payload=dict(
        ordertype="limit",
        type="buy",
        volume="1.25",
        pair="BTCUSD",
        price="27500",
        validate=True  # Does not really place the order, only validates it
    )
))
```

## Websockets Client
```python
import asyncio

from kraken_client.rest import RESTKrakenClient
from kraken_client.ws import WSKrakenClient, WSKrakenInMsg


async def recv_msgs(websocket):
    async for msg in websocket:
        await handle_msg(WSKrakenInMsg(msg))

async def handle_msg(msg: WSKrakenInMsg):
    # Insert your custom logic here to process incoming messages
    match msg.payload:
        case {'event' : 'heartbeat'}:
            pass
        case _:
            print(msg.payload)

async def main():
    # By default, both a "public" socket and a "private" socket are created, 
    # if you want to just open the public one set open_auth_socket to False.
    async with WSKrakenClient(open_auth_socket=True) as client:
        # Receive public messages
        recv_task = asyncio.create_task(recv_msgs(client.websocket))
        # Receive private messages
        auth_recv_task = asyncio.create_task(recv_msgs(client.auth_websocket))

        # Receive ticker information on currency pair
        await client.subscribe_ticker(pair=["BTC/EUR"])

        # At least one private message should be subscribed to keep the authenticated client 
        # connection open therefore we subscribe to openOrders
        # We can use the REST client to retrieve a valid token for websockets authentication
        kc = RESTKrakenClient()
        auth_token = kc.get_websockets_token().out_json['token']
        await client.subscribe_open_orders(token=auth_token)

        # Place a limit order
        await client.add_order(
            token=auth_token, ordertype="limit", pair="BTC/EUR",
            price="9000", type="buy", volume="0.0005",
            validate="true"  # Does not really place the order but only validates it
        )

        # Stop receiving ticker information
        await asyncio.sleep(0)
        await client.unsubscribe_ticker(pair=["BTC/EUR"])

        await recv_task
        await auth_recv_task

asyncio.run(main())
```
