#pragma once

// HTTP + WebSocket/SSE host API for the virtual drive.
// Stdlib + POSIX sockets only. No authentication.
// Binds 127.0.0.1 unless allow_remote is set. Do not expose this on an untrusted network.
// SHA-1 is used only to compute Sec-WebSocket-Accept (RFC 6455), not for passwords.

#include "emec/device/device.hpp"
#include "emec/json_lite.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <cctype>
#include <csignal>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace emec {

inline constexpr double MAX_STREAM_RATE_HZ = 50.0;
inline constexpr int MAX_TELEMETRY_SAMPLES = 100000;
inline constexpr const char* WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
inline constexpr std::size_t MAX_HTTP_BODY = 1 << 20;

struct Sha1Digest {
    std::uint8_t bytes[20]{};
};

inline std::uint32_t sha1_rotl(std::uint32_t value, int bits) {
    return (value << bits) | (value >> (32 - bits));
}

// RFC 3174 SHA-1. Used only for the WebSocket handshake accept key.
inline Sha1Digest sha1(const std::uint8_t* data, std::size_t length) {
    std::uint32_t h0 = 0x67452301;
    std::uint32_t h1 = 0xEFCDAB89;
    std::uint32_t h2 = 0x98BADCFE;
    std::uint32_t h3 = 0x10325476;
    std::uint32_t h4 = 0xC3D2E1F0;

    const std::uint64_t bit_length = static_cast<std::uint64_t>(length) * 8;
    std::vector<std::uint8_t> message(data, data + length);
    message.push_back(0x80);
    while ((message.size() % 64) != 56) {
        message.push_back(0);
    }
    for (int shift = 56; shift >= 0; shift -= 8) {
        message.push_back(static_cast<std::uint8_t>((bit_length >> shift) & 0xFF));
    }

    for (std::size_t offset = 0; offset < message.size(); offset += 64) {
        std::uint32_t w[80];
        for (int i = 0; i < 16; ++i) {
            w[i] = (static_cast<std::uint32_t>(message[offset + i * 4]) << 24) |
                   (static_cast<std::uint32_t>(message[offset + i * 4 + 1]) << 16) |
                   (static_cast<std::uint32_t>(message[offset + i * 4 + 2]) << 8) |
                   static_cast<std::uint32_t>(message[offset + i * 4 + 3]);
        }
        for (int i = 16; i < 80; ++i) {
            w[i] = sha1_rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
        }
        std::uint32_t a = h0, b = h1, c = h2, d = h3, e = h4;
        for (int i = 0; i < 80; ++i) {
            std::uint32_t f = 0;
            std::uint32_t k = 0;
            if (i < 20) {
                f = (b & c) | ((~b) & d);
                k = 0x5A827999;
            } else if (i < 40) {
                f = b ^ c ^ d;
                k = 0x6ED9EBA1;
            } else if (i < 60) {
                f = (b & c) | (b & d) | (c & d);
                k = 0x8F1BBCDC;
            } else {
                f = b ^ c ^ d;
                k = 0xCA62C1D6;
            }
            const std::uint32_t temp = sha1_rotl(a, 5) + f + e + k + w[i];
            e = d;
            d = c;
            c = sha1_rotl(b, 30);
            b = a;
            a = temp;
        }
        h0 += a;
        h1 += b;
        h2 += c;
        h3 += d;
        h4 += e;
    }
    Sha1Digest digest;
    const std::uint32_t words[5] = {h0, h1, h2, h3, h4};
    for (int i = 0; i < 5; ++i) {
        digest.bytes[i * 4] = static_cast<std::uint8_t>((words[i] >> 24) & 0xFF);
        digest.bytes[i * 4 + 1] = static_cast<std::uint8_t>((words[i] >> 16) & 0xFF);
        digest.bytes[i * 4 + 2] = static_cast<std::uint8_t>((words[i] >> 8) & 0xFF);
        digest.bytes[i * 4 + 3] = static_cast<std::uint8_t>(words[i] & 0xFF);
    }
    return digest;
}

inline std::string base64_encode(const std::uint8_t* data, std::size_t length) {
    static const char* table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve(((length + 2) / 3) * 4);
    for (std::size_t i = 0; i < length; i += 3) {
        const std::uint32_t n = (static_cast<std::uint32_t>(data[i]) << 16) |
                                ((i + 1 < length ? data[i + 1] : 0) << 8) |
                                (i + 2 < length ? data[i + 2] : 0);
        out.push_back(table[(n >> 18) & 63]);
        out.push_back(table[(n >> 12) & 63]);
        out.push_back(i + 1 < length ? table[(n >> 6) & 63] : '=');
        out.push_back(i + 2 < length ? table[n & 63] : '=');
    }
    return out;
}

inline std::string websocket_accept_key(const std::string& client_key) {
    const std::string material = client_key + WS_GUID;
    const Sha1Digest digest = sha1(reinterpret_cast<const std::uint8_t*>(material.data()), material.size());
    return base64_encode(digest.bytes, 20);
}

inline std::string ws_text_frame(const std::string& payload) {
    std::string frame;
    frame.push_back(static_cast<char>(0x81));
    const std::size_t n = payload.size();
    if (n < 126) {
        frame.push_back(static_cast<char>(n));
    } else if (n < 65536) {
        frame.push_back(static_cast<char>(126));
        frame.push_back(static_cast<char>((n >> 8) & 0xFF));
        frame.push_back(static_cast<char>(n & 0xFF));
    } else {
        frame.push_back(static_cast<char>(127));
        for (int shift = 56; shift >= 0; shift -= 8) {
            frame.push_back(static_cast<char>((static_cast<unsigned long long>(n) >> shift) & 0xFF));
        }
    }
    frame += payload;
    return frame;
}

inline bool is_loopback_host(const std::string& host) {
    return host == "127.0.0.1" || host == "localhost" || host == "::1";
}

struct HttpRequest {
    std::string method;
    std::string path;
    std::string query;
    std::map<std::string, std::string> headers;
    std::string body;
};

inline std::string header_get(const HttpRequest& request, const std::string& name) {
    for (const auto& header : request.headers) {
        if (header.first.size() == name.size()) {
            bool match = true;
            for (std::size_t i = 0; i < name.size(); ++i) {
                if (std::tolower(static_cast<unsigned char>(header.first[i])) !=
                    std::tolower(static_cast<unsigned char>(name[i]))) {
                    match = false;
                    break;
                }
            }
            if (match) {
                return header.second;
            }
        }
    }
    return "";
}

inline std::map<std::string, std::string> parse_query(const std::string& query) {
    std::map<std::string, std::string> out;
    std::size_t i = 0;
    while (i < query.size()) {
        const std::size_t amp = query.find('&', i);
        const std::string pair = query.substr(i, amp == std::string::npos ? std::string::npos : amp - i);
        const std::size_t eq = pair.find('=');
        if (eq != std::string::npos) {
            out[pair.substr(0, eq)] = pair.substr(eq + 1);
        }
        if (amp == std::string::npos) {
            break;
        }
        i = amp + 1;
    }
    return out;
}

inline Json register_payload(Register reg) {
    const auto& info = register_info(reg);
    Json entry = Json::object();
    entry.set("name", Json::str(register_name(reg)));
    entry.set("address", Json::number(static_cast<int>(reg)));
    entry.set("access", Json::str(access_name(info.access)));
    entry.set("unit", Json::str(info.unit));
    entry.set("description", Json::str(info.description));
    if (info.value_range) {
        Json range = Json::array();
        range.push(Json::number(info.value_range->first));
        range.push(Json::number(info.value_range->second));
        entry.set("range", std::move(range));
    } else {
        entry.set("range", Json::null());
    }
    return entry;
}

inline Json json_from_register_value(const RegisterValue& value) {
    if (std::holds_alternative<std::string>(value)) {
        return Json::str(std::get<std::string>(value));
    }
    return Json::number(std::get<double>(value));
}

inline Json sample_json(const TelemetrySample& sample) {
    Json object = Json::object();
    for (std::size_t i = 0; i < TELEMETRY_FIELDS.size(); ++i) {
        object.set(TELEMETRY_FIELDS[i], Json::number(sample.values[i]));
    }
    return object;
}

inline Json state_payload(const VirtualHardwareDevice& device) {
    Json payload = Json::object();
    payload.set("state", Json::str(device_state_name(device.state)));
    payload.set("status_word", Json::number(device.read_number(Register::STATUS_WORD)));
    payload.set("fault_code", Json::number(device.read_number(Register::FAULT_CODE)));
    payload.set("simulation_time", Json::number(device.read_number(Register::SIMULATION_TIME)));
    return payload;
}

inline Json stream_payload(const VirtualHardwareDevice& device) {
    Json payload = Json::object();
    payload.set("state", Json::str(device_state_name(device.state)));
    payload.set("fault_code", Json::number(device.read_number(Register::FAULT_CODE)));
    if (auto latest = device.telemetry.latest()) {
        payload.set("sample", sample_json(*latest));
    } else {
        payload.set("sample", Json::null());
    }
    return payload;
}

class DeviceServer {
public:
    DeviceServer(VirtualHardwareDevice& device, std::string host = "127.0.0.1", int port = 8080, bool allow_remote = false)
        : device_(device), host_(std::move(host)), port_(port) {
        if (port_ < 0 || port_ > 65535) {
            throw std::invalid_argument("port out of range");
        }
        if (!allow_remote && !is_loopback_host(host_)) {
            throw std::invalid_argument(
                "Refusing to bind a non-loopback interface without allow_remote. "
                "The device server has no authentication.");
        }
        if (host_ == "localhost") {
            host_ = "127.0.0.1";
        }
        if (host_ == "::1") {
            throw std::invalid_argument("C++ device server binds IPv4; use 127.0.0.1");
        }
        std::signal(SIGPIPE, SIG_IGN);
        listen_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (listen_fd_ < 0) {
            throw std::runtime_error("socket() failed");
        }
        int reuse = 1;
        ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(static_cast<std::uint16_t>(port_));
        if (::inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
            ::close(listen_fd_);
            listen_fd_ = -1;
            throw std::invalid_argument("invalid bind address: " + host_);
        }
        if (::bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
            ::close(listen_fd_);
            listen_fd_ = -1;
            throw std::runtime_error("bind() failed");
        }
        if (::listen(listen_fd_, 16) != 0) {
            ::close(listen_fd_);
            listen_fd_ = -1;
            throw std::runtime_error("listen() failed");
        }
        sockaddr_in bound{};
        socklen_t len = sizeof(bound);
        if (::getsockname(listen_fd_, reinterpret_cast<sockaddr*>(&bound), &len) == 0) {
            port_ = ntohs(bound.sin_port);
        }
    }

    ~DeviceServer() { shutdown(); }

    DeviceServer(const DeviceServer&) = delete;
    DeviceServer& operator=(const DeviceServer&) = delete;

    int port() const { return port_; }
    const std::string& host() const { return host_; }

    void serve_forever() {
        running_ = true;
        while (running_) {
            sockaddr_in client{};
            socklen_t len = sizeof(client);
            const int fd = ::accept(listen_fd_, reinterpret_cast<sockaddr*>(&client), &len);
            if (fd < 0) {
                if (!running_) {
                    break;
                }
                continue;
            }
            std::thread(&DeviceServer::handle_client, this, fd).detach();
        }
    }

    std::thread start_background() {
        return std::thread([this] { serve_forever(); });
    }

    void shutdown() {
        running_ = false;
        if (listen_fd_ >= 0) {
            ::shutdown(listen_fd_, SHUT_RDWR);
            ::close(listen_fd_);
            listen_fd_ = -1;
        }
    }

private:
    void handle_client(int fd) {
        try {
            HttpRequest request;
            if (!read_request(fd, request)) {
                ::close(fd);
                return;
            }
            if (request.method == "GET" && request.path == "/stream" && websocket_requested(request)) {
                handle_websocket(fd, request);
                return;
            }
            if (request.method == "GET" && request.path == "/stream") {
                handle_sse(fd, request);
                return;
            }
            const std::string response = dispatch(request);
            send_all(fd, response);
        } catch (...) {
        }
        ::close(fd);
    }

    static bool send_all(int fd, const std::string& data) {
        std::size_t sent = 0;
        while (sent < data.size()) {
            const ssize_t n = ::send(fd, data.data() + sent, data.size() - sent, MSG_NOSIGNAL);
            if (n <= 0) {
                return false;
            }
            sent += static_cast<std::size_t>(n);
        }
        return true;
    }

    static bool read_request(int fd, HttpRequest& request) {
        std::string raw;
        char buffer[4096];
        while (raw.find("\r\n\r\n") == std::string::npos) {
            const ssize_t n = ::recv(fd, buffer, sizeof(buffer), 0);
            if (n <= 0) {
                return false;
            }
            raw.append(buffer, buffer + n);
            if (raw.size() > MAX_HTTP_BODY) {
                return false;
            }
        }
        const std::size_t header_end = raw.find("\r\n\r\n");
        const std::string header = raw.substr(0, header_end);
        std::string body = raw.substr(header_end + 4);
        std::istringstream lines(header);
        std::string request_line;
        if (!std::getline(lines, request_line)) {
            return false;
        }
        if (!request_line.empty() && request_line.back() == '\r') {
            request_line.pop_back();
        }
        std::istringstream req(request_line);
        std::string target;
        std::string version;
        req >> request.method >> target >> version;
        const std::size_t q = target.find('?');
        request.path = q == std::string::npos ? target : target.substr(0, q);
        request.query = q == std::string::npos ? "" : target.substr(q + 1);
        if (request.path.size() > 1 && request.path.back() == '/') {
            request.path.pop_back();
        }
        std::string line;
        while (std::getline(lines, line)) {
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            const std::size_t colon = line.find(':');
            if (colon == std::string::npos) {
                continue;
            }
            std::string key = line.substr(0, colon);
            std::string value = line.substr(colon + 1);
            while (!value.empty() && value.front() == ' ') {
                value.erase(value.begin());
            }
            request.headers[key] = value;
        }
        std::size_t content_length = 0;
        const std::string length_text = header_get(request, "Content-Length");
        if (!length_text.empty()) {
            try {
                content_length = static_cast<std::size_t>(std::stoul(length_text));
            } catch (...) {
                return false;
            }
        }
        if (content_length > MAX_HTTP_BODY) {
            return false;
        }
        while (body.size() < content_length) {
            const ssize_t n = ::recv(fd, buffer, sizeof(buffer), 0);
            if (n <= 0) {
                return false;
            }
            body.append(buffer, buffer + n);
        }
        request.body = body.substr(0, content_length);
        return true;
    }

    std::string dispatch(const HttpRequest& request) {
        try {
            if (request.method == "GET" && request.path == "/registers") {
                Json out = Json::object();
                for (Register reg : kAllRegisters) {
                    Json entry = register_payload(reg);
                    if (register_info(reg).access != Access::WRITE_ONLY) {
                        try {
                            entry.set("value", json_from_register_value(device_.read_register(reg)));
                        } catch (...) {
                            entry.set("value", Json::null());
                        }
                    }
                    out.set(register_name(reg), std::move(entry));
                }
                return http_json(200, out.dump());
            }
            if (request.method == "GET" && request.path.rfind("/registers/", 0) == 0) {
                const std::string name = request.path.substr(std::string("/registers/").size());
                try {
                    RegisterValue value = device_.read_register(name);
                    auto reg = register_from_name(name);
                    Json payload = register_payload(*reg);
                    payload.set("value", json_from_register_value(value));
                    return http_json(200, payload.dump());
                } catch (const RegisterAccessError& error) {
                    return http_error(404, error.what());
                }
            }
            if (request.method == "GET" && request.path == "/telemetry") {
                const auto query = parse_query(request.query);
                std::optional<int> last_n;
                if (query.count("last_n")) {
                    last_n = std::stoi(query.at("last_n"));
                    if (*last_n > MAX_TELEMETRY_SAMPLES) {
                        last_n = MAX_TELEMETRY_SAMPLES;
                    }
                }
                Json samples = Json::array();
                for (const auto& sample : device_.telemetry.snapshot(last_n)) {
                    samples.push(sample_json(sample));
                }
                Json payload = Json::object();
                payload.set("samples", std::move(samples));
                return http_json(200, payload.dump());
            }
            if (request.method == "GET" && request.path == "/state") {
                return http_json(200, state_payload(device_).dump());
            }
            if (request.method == "POST" && request.path.rfind("/registers/", 0) == 0) {
                const std::string name = request.path.substr(std::string("/registers/").size());
                auto body = parse_json(request.body);
                const Json* value = body ? body->find("value") : nullptr;
                if (!body || !value || value->type() != Json::Type::Number) {
                    return http_error(400, "Body must be JSON: {\"value\": <number>}");
                }
                try {
                    device_.write_register(name, value->number_value());
                    Json payload = Json::object();
                    payload.set("ok", Json::boolean(true));
                    payload.set("register", Json::str(name));
                    payload.set("state", Json::str(device_state_name(device_.state)));
                    return http_json(200, payload.dump());
                } catch (const RegisterAccessError& error) {
                    return http_error(404, error.what());
                } catch (const RegisterValueError& error) {
                    return http_error(400, error.what());
                } catch (const InvalidStateError& error) {
                    return http_error(400, error.what());
                }
            }
            if (request.method == "POST" && request.path.rfind("/command/", 0) == 0) {
                const std::string cmd = request.path.substr(std::string("/command/").size());
                try {
                    DeviceState state = DeviceState::OFF;
                    if (cmd == "power_on") {
                        state = device_.power_on();
                    } else if (cmd == "power_off") {
                        state = device_.power_off();
                    } else if (cmd == "start") {
                        state = device_.start();
                    } else if (cmd == "stop") {
                        state = device_.stop();
                    } else if (cmd == "reset") {
                        state = device_.reset();
                    } else if (cmd == "estop") {
                        state = device_.e_stop();
                    } else {
                        return http_error(404, "Unknown command: " + cmd);
                    }
                    Json payload = Json::object();
                    payload.set("ok", Json::boolean(true));
                    payload.set("state", Json::str(device_state_name(state)));
                    return http_json(200, payload.dump());
                } catch (const InvalidStateError& error) {
                    return http_error(409, error.what());
                }
            }
            return http_error(404, "Unknown path: " + request.path);
        } catch (const std::exception& error) {
            return http_error(400, error.what());
        }
    }

    static bool websocket_requested(const HttpRequest& request) {
        const std::string upgrade = header_get(request, "Upgrade");
        for (char ch : upgrade) {
            if (std::tolower(static_cast<unsigned char>(ch)) == 'w') {
                return upgrade.find("websocket") != std::string::npos || upgrade.find("WebSocket") != std::string::npos ||
                       upgrade.find("WEBSOCKET") != std::string::npos;
            }
        }
        std::string lower = upgrade;
        for (char& ch : lower) {
            ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
        }
        return lower.find("websocket") != std::string::npos;
    }

    void handle_websocket(int fd, const HttpRequest& request) {
        const std::string key = header_get(request, "Sec-WebSocket-Key");
        if (key.empty()) {
            send_all(fd, http_error(400, "Missing Sec-WebSocket-Key"));
            ::close(fd);
            return;
        }
        const std::string accept = websocket_accept_key(key);
        std::ostringstream handshake;
        handshake << "HTTP/1.1 101 Switching Protocols\r\n"
                  << "Upgrade: websocket\r\n"
                  << "Connection: Upgrade\r\n"
                  << "Sec-WebSocket-Accept: " << accept << "\r\n\r\n";
        if (!send_all(fd, handshake.str())) {
            ::close(fd);
            return;
        }
        const double rate = stream_rate(request);
        const auto interval = std::chrono::duration<double>(1.0 / rate);
        while (running_) {
            const std::string frame = ws_text_frame(stream_payload(device_).dump());
            if (!send_all(fd, frame)) {
                break;
            }
            std::this_thread::sleep_for(interval);
        }
        ::close(fd);
    }

    void handle_sse(int fd, const HttpRequest& request) {
        const std::string headers =
            "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\n\r\n";
        if (!send_all(fd, headers)) {
            ::close(fd);
            return;
        }
        const double rate = stream_rate(request);
        const auto interval = std::chrono::duration<double>(1.0 / rate);
        while (running_) {
            const std::string event = "data: " + stream_payload(device_).dump() + "\n\n";
            if (!send_all(fd, event)) {
                break;
            }
            std::this_thread::sleep_for(interval);
        }
        ::close(fd);
    }

    static double stream_rate(const HttpRequest& request) {
        const auto query = parse_query(request.query);
        double rate = 10.0;
        if (query.count("rate_hz")) {
            try {
                rate = std::stod(query.at("rate_hz"));
            } catch (...) {
                rate = 10.0;
            }
        }
        if (rate < 0.1) {
            rate = 0.1;
        }
        if (rate > MAX_STREAM_RATE_HZ) {
            rate = MAX_STREAM_RATE_HZ;
        }
        return rate;
    }

    static std::string http_json(int status, const std::string& body) { return http_response(status, "application/json", body); }

    static std::string http_error(int status, const std::string& message) {
        Json payload = Json::object();
        payload.set("error", Json::str(message));
        return http_json(status, payload.dump());
    }

    static std::string http_response(int status, const std::string& content_type, const std::string& body) {
        const char* reason = "OK";
        if (status == 400) {
            reason = "Bad Request";
        } else if (status == 404) {
            reason = "Not Found";
        } else if (status == 409) {
            reason = "Conflict";
        }
        std::ostringstream out;
        out << "HTTP/1.1 " << status << ' ' << reason << "\r\n"
            << "Content-Type: " << content_type << "\r\n"
            << "Content-Length: " << body.size() << "\r\n"
            << "Connection: close\r\n\r\n"
            << body;
        return out.str();
    }

    VirtualHardwareDevice& device_;
    std::string host_;
    int port_;
    int listen_fd_ = -1;
    std::atomic<bool> running_{false};
};

struct HttpResponse {
    int status = 0;
    std::string body;
    std::string headers;
};

inline HttpResponse http_exchange(const std::string& host,
                                  int port,
                                  const std::string& method,
                                  const std::string& path,
                                  const std::string& body = "",
                                  const std::string& extra_headers = "") {
    const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        throw std::runtime_error("socket() failed");
    }
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<std::uint16_t>(port));
    if (::inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
        ::close(fd);
        throw std::invalid_argument("invalid host");
    }
    if (::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        ::close(fd);
        throw std::runtime_error("connect() failed");
    }
    std::ostringstream req;
    req << method << ' ' << path << " HTTP/1.1\r\nHost: " << host << "\r\nConnection: close\r\n";
    if (!body.empty()) {
        req << "Content-Type: application/json\r\nContent-Length: " << body.size() << "\r\n";
    }
    if (!extra_headers.empty()) {
        req << extra_headers;
        if (extra_headers.back() != '\n') {
            req << "\r\n";
        }
    }
    req << "\r\n" << body;
    const std::string request = req.str();
    std::size_t sent = 0;
    while (sent < request.size()) {
        const ssize_t n = ::send(fd, request.data() + sent, request.size() - sent, MSG_NOSIGNAL);
        if (n <= 0) {
            ::close(fd);
            throw std::runtime_error("send() failed");
        }
        sent += static_cast<std::size_t>(n);
    }
    std::string raw;
    char buffer[4096];
    while (true) {
        const ssize_t n = ::recv(fd, buffer, sizeof(buffer), 0);
        if (n <= 0) {
            break;
        }
        raw.append(buffer, buffer + n);
    }
    ::close(fd);
    HttpResponse response;
    const std::size_t header_end = raw.find("\r\n\r\n");
    if (header_end == std::string::npos) {
        throw std::runtime_error("incomplete HTTP response");
    }
    response.headers = raw.substr(0, header_end);
    response.body = raw.substr(header_end + 4);
    const std::size_t space = response.headers.find(' ');
    if (space != std::string::npos) {
        response.status = std::stoi(response.headers.substr(space + 1));
    }
    return response;
}

inline std::pair<std::unique_ptr<DeviceServer>, std::thread> serve(VirtualHardwareDevice& device,
                                                                  const std::string& host = "127.0.0.1",
                                                                  int port = 8080,
                                                                  bool background = false,
                                                                  bool allow_remote = false) {
    auto server = std::make_unique<DeviceServer>(device, host, port, allow_remote);
    if (background) {
        std::thread thread = server->start_background();
        // Give the accept loop a moment to enter accept() before tests connect.
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        return {std::move(server), std::move(thread)};
    }
    server->serve_forever();
    return {std::move(server), std::thread()};
}

}  // namespace emec
