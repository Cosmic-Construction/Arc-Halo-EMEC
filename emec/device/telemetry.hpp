#pragma once

// Fixed-window telemetry ring buffer over VirtualEngine.export_data() channels.
// Decimation records every Nth offered sample. CSV export keeps channel order.

#include <array>
#include <deque>
#include <fstream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace emec {

inline constexpr std::array<const char*, 9> TELEMETRY_FIELDS = {
    "time",
    "speed_rpm",
    "torque",
    "power_mechanical",
    "power_electrical",
    "efficiency",
    "stator_current_a",
    "stator_current_b",
    "stator_current_c",
};

struct TelemetrySample {
    std::array<double, TELEMETRY_FIELDS.size()> values{};

    double at(std::string_view key) const {
        for (std::size_t i = 0; i < TELEMETRY_FIELDS.size(); ++i) {
            if (key == TELEMETRY_FIELDS[i]) {
                return values[i];
            }
        }
        throw std::out_of_range("unknown telemetry channel");
    }

    bool contains(std::string_view key) const {
        for (const char* field : TELEMETRY_FIELDS) {
            if (key == field) {
                return true;
            }
        }
        return false;
    }

    void set(std::string_view key, double value) {
        for (std::size_t i = 0; i < TELEMETRY_FIELDS.size(); ++i) {
            if (key == TELEMETRY_FIELDS[i]) {
                values[i] = value;
                return;
            }
        }
    }
};

class TelemetryRecorder {
public:
    explicit TelemetryRecorder(int capacity = 10000, int decimation = 1) : capacity_(capacity), decimation_(decimation) {
        if (capacity < 1) {
            throw std::invalid_argument("capacity must be >= 1");
        }
        if (decimation < 1) {
            throw std::invalid_argument("decimation must be >= 1");
        }
    }

    int capacity() const { return capacity_; }
    int decimation() const { return decimation_; }

    bool record(const TelemetrySample& sample) {
        ++tick_;
        if (tick_ % decimation_ != 0) {
            return false;
        }
        if (static_cast<int>(buffer_.size()) == capacity_) {
            buffer_.pop_front();
        }
        buffer_.push_back(sample);
        return true;
    }

    // Accept a partial sample: missing channels are stored as 0.
    bool record_partial(const std::vector<std::pair<std::string, double>>& fields) {
        TelemetrySample sample;
        for (const auto& field : fields) {
            if (sample.contains(field.first)) {
                sample.set(field.first, field.second);
            }
        }
        return record(sample);
    }

    std::vector<TelemetrySample> snapshot(std::optional<int> last_n = std::nullopt) const {
        std::vector<TelemetrySample> samples(buffer_.begin(), buffer_.end());
        if (last_n && *last_n >= 0 && static_cast<std::size_t>(*last_n) < samples.size()) {
            samples.erase(samples.begin(), samples.end() - *last_n);
        }
        return samples;
    }

    std::optional<TelemetrySample> latest() const {
        if (buffer_.empty()) {
            return std::nullopt;
        }
        return buffer_.back();
    }

    std::size_t size() const { return buffer_.size(); }
    bool empty() const { return buffer_.empty(); }

    void clear() {
        buffer_.clear();
        tick_ = 0;
    }

    std::string to_csv(std::optional<int> last_n = std::nullopt) const {
        std::ostringstream out;
        for (std::size_t i = 0; i < TELEMETRY_FIELDS.size(); ++i) {
            if (i) {
                out << ',';
            }
            out << TELEMETRY_FIELDS[i];
        }
        out << '\n';
        for (const auto& sample : snapshot(last_n)) {
            for (std::size_t i = 0; i < TELEMETRY_FIELDS.size(); ++i) {
                if (i) {
                    out << ',';
                }
                out << sample.values[i];
            }
            out << '\n';
        }
        return out.str();
    }

    void export_csv(const std::string& path, std::optional<int> last_n = std::nullopt) const {
        std::ofstream file(path);
        if (!file) {
            throw std::runtime_error("failed to open telemetry CSV: " + path);
        }
        file << to_csv(last_n);
    }

private:
    int capacity_;
    int decimation_;
    std::deque<TelemetrySample> buffer_;
    int tick_ = 0;
};

}  // namespace emec
