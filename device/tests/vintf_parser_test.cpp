// SPDX-License-Identifier: Apache-2.0
// Synthetic fixtures only; no device identifiers or private vendor XML.
#include <vintf/HalManifest.h>
#include <vintf/parse_xml.h>
#include <cstdlib>
#include <iostream>
#include <set>
#include <string>

static void require(bool condition, const std::string& message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

int main() {
    const std::string body = R"(<hal format="aidl">
        <name>android.hardware.security.keymint</name><version>2</version>
        <interface><name>IKeyMintDevice</name><instance>default</instance></interface>
    </hal></manifest>)";
    for (const auto* version : {"4.0", "5.0"}) {
        android::vintf::HalManifest manifest;
        std::string error;
        const std::string xml = std::string("<manifest version=\"") + version +
            "\" type=\"device\" target-level=\"7\">" + body;
        require(android::vintf::fromXml(&manifest, xml, &error), error);
        for (size_t requested : {1u, 2u}) {
            const auto instances = manifest.getAidlInstances(
                "android.hardware.security.keymint", requested, "IKeyMintDevice");
            require(instances == std::set<std::string>{"default"},
                    "KeyMint v2 must be discoverable by compatible v1/v2 clients");
        }
        require(manifest.getAidlInstances("android.hardware.security.keymint", 3,
                "IKeyMintDevice").empty(), "Must not invent a KeyMint v3 instance");
    }
    for (const auto& xml : {std::string("<manifest"),
            std::string("<manifest version=\"99.0\" type=\"device\">") + body}) {
        android::vintf::HalManifest manifest;
        std::string error;
        require(!android::vintf::fromXml(&manifest, xml, &error),
                "Malformed/future schema must still be rejected");
        require(!error.empty(), "Rejected input must report a diagnostic");
    }
    std::cout << "PASS: schema 4/5, KeyMint v1/v2/v3 discovery, malformed/future rejection\n";
}
