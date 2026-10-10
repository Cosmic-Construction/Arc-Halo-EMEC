#pragma once

// Minimal JSON writer/parser for the device host API.
// Enough for register payloads, telemetry samples, and {"value": <number>} writes.
// Not a general JSON library.

#include <cctype>
#include <cmath>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

namespace emec {

class Json {
public:
    enum class Type { Null, Bool, Number, String, Array, Object };

    Json() = default;
    static Json null() { return Json(); }
    static Json boolean(bool value) {
        Json json;
        json.type_ = Type::Bool;
        json.bool_ = value;
        return json;
    }
    static Json number(double value) {
        Json json;
        json.type_ = Type::Number;
        json.number_ = value;
        return json;
    }
    static Json str(std::string value) {
        Json json;
        json.type_ = Type::String;
        json.string_ = std::move(value);
        return json;
    }
    static Json array() {
        Json json;
        json.type_ = Type::Array;
        return json;
    }
    static Json object() {
        Json json;
        json.type_ = Type::Object;
        return json;
    }

    Type type() const { return type_; }
    bool is_null() const { return type_ == Type::Null; }
    double number_value() const { return number_; }
    const std::string& string_value() const { return string_; }

    void push(Json value) { items_.push_back(std::move(value)); }
    void set(const std::string& key, Json value) { fields_[key] = std::move(value); }

    const Json* find(const std::string& key) const {
        auto it = fields_.find(key);
        if (it == fields_.end()) {
            return nullptr;
        }
        return &it->second;
    }

    std::string dump() const {
        std::ostringstream out;
        write(out);
        return out.str();
    }

private:
    void write(std::ostream& out) const {
        switch (type_) {
            case Type::Null: out << "null"; break;
            case Type::Bool: out << (bool_ ? "true" : "false"); break;
            case Type::Number: write_number(out, number_); break;
            case Type::String: write_string(out, string_); break;
            case Type::Array: {
                out << '[';
                for (std::size_t i = 0; i < items_.size(); ++i) {
                    if (i) {
                        out << ',';
                    }
                    items_[i].write(out);
                }
                out << ']';
                break;
            }
            case Type::Object: {
                out << '{';
                bool first = true;
                for (const auto& field : fields_) {
                    if (!first) {
                        out << ',';
                    }
                    first = false;
                    write_string(out, field.first);
                    out << ':';
                    field.second.write(out);
                }
                out << '}';
                break;
            }
        }
    }

    static void write_number(std::ostream& out, double value) {
        if (!std::isfinite(value)) {
            out << "null";
            return;
        }
        std::ostringstream tmp;
        tmp.setf(std::ios::fixed);
        tmp.precision(6);
        tmp << value;
        std::string text = tmp.str();
        while (text.size() > 1 && text.back() == '0') {
            text.pop_back();
        }
        if (!text.empty() && text.back() == '.') {
            text.push_back('0');
        }
        out << text;
    }

    static void write_string(std::ostream& out, const std::string& value) {
        out << '"';
        for (unsigned char ch : value) {
            switch (ch) {
                case '"': out << "\\\""; break;
                case '\\': out << "\\\\"; break;
                case '\n': out << "\\n"; break;
                case '\r': out << "\\r"; break;
                case '\t': out << "\\t"; break;
                default:
                    if (ch < 0x20) {
                        out << "\\u00";
                        const char* hex = "0123456789abcdef";
                        out << hex[ch >> 4] << hex[ch & 0xF];
                    } else {
                        out << static_cast<char>(ch);
                    }
            }
        }
        out << '"';
    }

    Type type_ = Type::Null;
    bool bool_ = false;
    double number_ = 0.0;
    std::string string_;
    std::vector<Json> items_;
    std::map<std::string, Json> fields_;
};

inline void skip_ws(std::string_view text, std::size_t& i) {
    while (i < text.size() && std::isspace(static_cast<unsigned char>(text[i]))) {
        ++i;
    }
}

inline std::optional<Json> parse_json(std::string_view text);

inline std::optional<Json> parse_json_at(std::string_view text, std::size_t& i) {
    skip_ws(text, i);
    if (i >= text.size()) {
        return std::nullopt;
    }
    if (text.compare(i, 4, "null") == 0) {
        i += 4;
        return Json::null();
    }
    if (text.compare(i, 4, "true") == 0) {
        i += 4;
        return Json::boolean(true);
    }
    if (text.compare(i, 5, "false") == 0) {
        i += 5;
        return Json::boolean(false);
    }
    if (text[i] == '"') {
        ++i;
        std::string value;
        while (i < text.size() && text[i] != '"') {
            if (text[i] == '\\' && i + 1 < text.size()) {
                ++i;
                value.push_back(text[i]);
            } else {
                value.push_back(text[i]);
            }
            ++i;
        }
        if (i >= text.size() || text[i] != '"') {
            return std::nullopt;
        }
        ++i;
        return Json::str(std::move(value));
    }
    if (text[i] == '-' || std::isdigit(static_cast<unsigned char>(text[i]))) {
        const std::size_t start = i;
        if (text[i] == '-') {
            ++i;
        }
        while (i < text.size() && (std::isdigit(static_cast<unsigned char>(text[i])) || text[i] == '.' || text[i] == 'e' ||
                                   text[i] == 'E' || text[i] == '+' || text[i] == '-')) {
            ++i;
        }
        try {
            return Json::number(std::stod(std::string(text.substr(start, i - start))));
        } catch (...) {
            return std::nullopt;
        }
    }
    if (text[i] == '{') {
        ++i;
        Json object = Json::object();
        skip_ws(text, i);
        if (i < text.size() && text[i] == '}') {
            ++i;
            return object;
        }
        while (i < text.size()) {
            auto key = parse_json_at(text, i);
            if (!key || key->type() != Json::Type::String) {
                return std::nullopt;
            }
            skip_ws(text, i);
            if (i >= text.size() || text[i] != ':') {
                return std::nullopt;
            }
            ++i;
            auto value = parse_json_at(text, i);
            if (!value) {
                return std::nullopt;
            }
            object.set(key->string_value(), std::move(*value));
            skip_ws(text, i);
            if (i < text.size() && text[i] == ',') {
                ++i;
                continue;
            }
            if (i < text.size() && text[i] == '}') {
                ++i;
                return object;
            }
            return std::nullopt;
        }
    }
    if (text[i] == '[') {
        ++i;
        Json array = Json::array();
        skip_ws(text, i);
        if (i < text.size() && text[i] == ']') {
            ++i;
            return array;
        }
        while (i < text.size()) {
            auto value = parse_json_at(text, i);
            if (!value) {
                return std::nullopt;
            }
            array.push(std::move(*value));
            skip_ws(text, i);
            if (i < text.size() && text[i] == ',') {
                ++i;
                continue;
            }
            if (i < text.size() && text[i] == ']') {
                ++i;
                return array;
            }
            return std::nullopt;
        }
    }
    return std::nullopt;
}

inline std::optional<Json> parse_json(std::string_view text) {
    std::size_t i = 0;
    return parse_json_at(text, i);
}

}  // namespace emec
