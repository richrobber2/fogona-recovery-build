#ifndef FOGONA_KEYSTORE_SERVICE_WAIT_H
#define FOGONA_KEYSTORE_SERVICE_WAIT_H
#include <algorithm>
#include <chrono>
namespace fogona {
// Only bounds polling for service registration; it does not bound later Binder calls.
template <class Check, class Now, class Pause>
auto WaitForKeystore(Check check, Now now, Pause pause,
                     std::chrono::milliseconds budget,
                     std::chrono::milliseconds interval) -> decltype(check()) {
    const auto deadline = now() + budget;
    for (;;) {
        auto service = check();
        if (service.get() != nullptr) return service;
        const auto current = now();
        if (current >= deadline) return {};
        pause(std::min(deadline, current + interval) - current);
    }
}
}  // namespace fogona
#endif
