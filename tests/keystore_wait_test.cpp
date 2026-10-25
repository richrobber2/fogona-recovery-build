#include "../tools/keystore-service-wait.h"
#include <cassert>
#include <memory>
using Clock = std::chrono::steady_clock;
using Ms = std::chrono::milliseconds;
int main() {
    // Immediate service: retain ownership and never sleep.
    {
        Clock::time_point time{}; int checks=0, sleeps=0;
        auto h=fogona::WaitForKeystore([&]{ ++checks; return std::make_unique<int>(42); },
            [&]{return time;}, [&](Clock::duration d){ ++sleeps; time+=d; },Ms(5000),Ms(100));
        assert(h && *h==42 && checks==1 && sleeps==0);
    }
    // Late service is still used; polling must not disable available crypto.
    {
        Clock::time_point time{}; int checks=0;
        auto h=fogona::WaitForKeystore([&]{ ++checks; return checks==4 ? std::make_unique<int>(7) : nullptr; },
            [&]{return time;}, [&](Clock::duration d){ time+=d; },Ms(5000),Ms(100));
        assert(h && *h==7 && time.time_since_epoch()==Ms(300));
    }
    // Missing service ends at the deadline; final sleep is clipped to budget.
    {
        Clock::time_point time{}; int checks=0;
        auto h=fogona::WaitForKeystore([&]() -> std::unique_ptr<int> { ++checks; return {}; },
            [&]{return time;}, [&](Clock::duration d){ assert(d>Clock::duration::zero()); time+=d; },Ms(250),Ms(100));
        assert(!h && checks==4 && time.time_since_epoch()==Ms(250));
    }
    // Zero budget still permits an immediately registered service, without sleep.
    {
        Clock::time_point time{};
        auto h=fogona::WaitForKeystore([]{return std::make_unique<int>(1);},[&]{return time;},
            [](Clock::duration){assert(false);},Ms(0),Ms(100));
        assert(h && *h==1);
    }
    // Absent service with zero budget returns safely, without sleep.
    {
        Clock::time_point time{};
        auto h=fogona::WaitForKeystore([]() -> std::unique_ptr<int> {return {};},[&]{return time;},
            [](Clock::duration){assert(false);},Ms(0),Ms(100));
        assert(!h);
    }
}
