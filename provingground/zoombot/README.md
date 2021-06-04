# Boombot Service

Zoombot is a test service that can create a conference rooms with the given
number of participants in the room upon the request from the clients (usually
test cases). A test case can obtain the conference room URL and join from its
own test scrips to test the conference room features.

Currently only Zoom conference room is supported.

The zoombot service will be running as a HTTP server and listen on the
configured IP address and port.

## Build and Run

To build the service, just run "make".

```shell
> make
```

A bin directory will be created with an executable "meet-server-headless".

Run the command with "--help" flag to see the help information:

```shell
bin/meet-server-headless --help
Usage of bin/meet-server-headless:
  -conf string
        meet target browser config file. See examples under conf/ dir.
  -http-svc-addr string
        http service listening address (default ":22223")
```

## API Definition

The test clients can issue test room request with the following HTTP message:

### 1. Request a meeting room

#### Request

```shell
GET http://<zoombot ip address>:<port>/api/room/zoom/createio?count=<count>&max_duration=<minutes>
```

Parameters

- count: participant number
- max_duration: maximum meeting duration in minutes

#### Response Body

```json
{
    url: <meeting url>
    room_id: <room idenfifier>
    err: <optional error message>
}
```

### 2. Request to close the meeting room

#### Request

```shell
GET http://<zoombot ip address>:<port>/api/room/zoom/endaio?room_id=<room id>
```

Parameters:

- room_id: The room_id returned from room meeting request.

#### Response Body

```json
{
    err: <optional error message>
}
```

## HTTP Request Authentication

The HTTP request must include a "Authorization" header with a valid
authentication token. Authentication tokens are configured in configuration
file.

```shell
    Authorization: Bearer <token>
```
