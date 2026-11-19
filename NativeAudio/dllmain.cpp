#include <Windows.h>
#include <mmsystem.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

namespace RC
{
#define RC_UE4SS_API __declspec(dllimport)

using StringType = std::wstring;
using StringViewType = std::wstring_view;

namespace GUI
{
class GUITab;
}

namespace LuaMadeSimple
{
class Lua;
using LuaFunction = int (*)(const Lua&);

class Lua
{
public:
    __declspec(dllimport) auto register_function(const std::string& name, const LuaFunction& function) const -> void;
    [[nodiscard]] __declspec(dllimport) auto is_string(int32_t force_index = 1) const -> bool;
    [[nodiscard]] __declspec(dllimport) auto get_string(int32_t force_index = 1) const -> std::string_view;
    [[nodiscard]] __declspec(dllimport) auto is_integer(int32_t force_index = 1) const -> bool;
    [[nodiscard]] __declspec(dllimport) auto get_integer(int32_t force_index = 1) const -> int64_t;
    [[nodiscard]] __declspec(dllimport) auto is_bool(int32_t force_index = 1) const -> bool;
    [[nodiscard]] __declspec(dllimport) auto get_bool(int32_t force_index = 1) const -> bool;
    __declspec(dllimport) auto set_bool(bool value) const -> void;
};
}

void write_mod_log(const wchar_t* message)
{
    HMODULE module{};
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       reinterpret_cast<LPCWSTR>(&write_mod_log), &module);

    wchar_t module_path[MAX_PATH]{};
    const DWORD length = GetModuleFileNameW(module, module_path, MAX_PATH);
    if (length == 0 || length >= MAX_PATH)
    {
        return;
    }

    auto log_path = std::filesystem::path(module_path).parent_path().parent_path() / L"native-audio.log";
    std::wofstream log(log_path, std::ios::app);
    if (log)
    {
        log << message << L'\n';
    }
}

class CppUserModBase
{
protected:
    std::vector<std::shared_ptr<GUI::GUITab>> GUITabs{};

public:
    StringType ModName{};
    StringType ModVersion{};
    StringType ModDescription{};
    StringType ModAuthors{};
    StringType ModIntendedSDKVersion{};

    RC_UE4SS_API CppUserModBase();
    RC_UE4SS_API virtual ~CppUserModBase();
    RC_UE4SS_API virtual auto on_update() -> void {}
    RC_UE4SS_API virtual auto on_unreal_init() -> void {}
    RC_UE4SS_API virtual auto on_ui_init() -> void {}
    RC_UE4SS_API virtual auto on_program_start() -> void {}
    RC_UE4SS_API virtual auto on_lua_start(StringViewType, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                           std::vector<LuaMadeSimple::Lua*>&) -> void {}
    RC_UE4SS_API virtual auto on_lua_start(LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                           std::vector<LuaMadeSimple::Lua*>&) -> void {}
    RC_UE4SS_API virtual auto on_lua_stop(StringViewType, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                          std::vector<LuaMadeSimple::Lua*>&) -> void {}
    RC_UE4SS_API virtual auto on_lua_stop(LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                          std::vector<LuaMadeSimple::Lua*>&) -> void {}
    RC_UE4SS_API virtual auto on_dll_load(std::wstring_view) -> void {}
    RC_UE4SS_API virtual auto render_tab() -> void {}
    RC_UE4SS_API virtual auto on_lua_start(StringViewType, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                           LuaMadeSimple::Lua*) -> void {}
    RC_UE4SS_API virtual auto on_lua_start(LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                           LuaMadeSimple::Lua*) -> void {}
    RC_UE4SS_API virtual auto on_lua_stop(StringViewType, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                          LuaMadeSimple::Lua*) -> void {}
    RC_UE4SS_API virtual auto on_lua_stop(LuaMadeSimple::Lua&, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                                          LuaMadeSimple::Lua*) -> void {}
    RC_UE4SS_API virtual auto on_cpp_mods_loaded() -> void {}
};

class AudioPlayer
{
    struct PcmData
    {
        WORD channels{};
        DWORD sample_rate{};
        WORD bits_per_sample{};
        std::vector<uint8_t> samples;
    };

    struct Voice
    {
        HWAVEOUT device{};
        WAVEHDR header{};
        std::vector<uint8_t> samples;
        int clip{};
        int64_t cast{};
    };

    std::array<PcmData, 7> clips_{};
    std::vector<std::unique_ptr<Voice>> voices_;
    std::unordered_set<int64_t> hit_casts_;
    int volume_{100};
    std::mutex mutex_;
    bool ready_{};

    static auto read_u16(const std::vector<uint8_t>& bytes, size_t offset) -> uint16_t
    {
        return static_cast<uint16_t>(bytes[offset]) | (static_cast<uint16_t>(bytes[offset + 1]) << 8);
    }

    static auto read_u32(const std::vector<uint8_t>& bytes, size_t offset) -> uint32_t
    {
        return static_cast<uint32_t>(bytes[offset]) | (static_cast<uint32_t>(bytes[offset + 1]) << 8)
             | (static_cast<uint32_t>(bytes[offset + 2]) << 16) | (static_cast<uint32_t>(bytes[offset + 3]) << 24);
    }

    static auto read_pcm(const std::filesystem::path& path) -> PcmData
    {
        std::ifstream file(path, std::ios::binary);
        if (!file)
        {
            throw std::runtime_error("could not open audio file");
        }

        std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(file)), {});
        if (bytes.size() < 12 || std::string_view(reinterpret_cast<const char*>(bytes.data()), 4) != "RIFF"
            || std::string_view(reinterpret_cast<const char*>(bytes.data() + 8), 4) != "WAVE")
        {
            throw std::runtime_error("audio file is not RIFF/WAVE");
        }

        PcmData pcm;
        bool has_format = false;
        size_t offset = 12;
        while (offset + 8 <= bytes.size())
        {
            const auto* chunk = reinterpret_cast<const char*>(bytes.data() + offset);
            const uint32_t size = read_u32(bytes, offset + 4);
            const size_t data_offset = offset + 8;
            if (static_cast<uint64_t>(data_offset) + size > bytes.size())
            {
                throw std::runtime_error("truncated WAV chunk");
            }

            if (std::string_view(chunk, 4) == "fmt ")
            {
                if (size < 16 || read_u16(bytes, data_offset) != WAVE_FORMAT_PCM)
                {
                    throw std::runtime_error("WAV must contain integer PCM data");
                }
                pcm.channels = read_u16(bytes, data_offset + 2);
                pcm.sample_rate = read_u32(bytes, data_offset + 4);
                pcm.bits_per_sample = read_u16(bytes, data_offset + 14);
                has_format = true;
            }
            else if (std::string_view(chunk, 4) == "data")
            {
                if (!has_format)
                {
                    throw std::runtime_error("WAV data chunk precedes its format chunk");
                }
                pcm.samples.assign(bytes.begin() + static_cast<ptrdiff_t>(data_offset),
                                   bytes.begin() + static_cast<ptrdiff_t>(data_offset + size));
                break;
            }
            offset = data_offset + size + (size & 1U);
        }

        if (!has_format || pcm.samples.empty() || (pcm.bits_per_sample != 16 && pcm.bits_per_sample != 8))
        {
            throw std::runtime_error("unsupported or empty PCM WAV");
        }
        return pcm;
    }

    static auto pcm_path() -> std::filesystem::path
    {
        HMODULE module{};
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCWSTR>(&pcm_path), &module);
        wchar_t module_path[MAX_PATH]{};
        const DWORD length = GetModuleFileNameW(module, module_path, MAX_PATH);
        if (length == 0 || length >= MAX_PATH)
        {
            throw std::runtime_error("could not resolve native mod directory");
        }
        return std::filesystem::path(module_path).parent_path().parent_path().parent_path()
             / L"PBZChiRenDarkSword" / L"Audio";
    }

    static auto scale_pcm(std::vector<uint8_t>& samples, int bits_per_sample, int volume) -> void
    {
        if (bits_per_sample == 16)
        {
            for (size_t i = 0; i + 1 < samples.size(); i += 2)
            {
                const int16_t sample = static_cast<int16_t>(read_u16(samples, i));
                const int scaled = std::clamp(static_cast<int>(sample) * volume / 100,
                                              static_cast<int>(INT16_MIN), static_cast<int>(INT16_MAX));
                const auto value = static_cast<uint16_t>(static_cast<int16_t>(scaled));
                samples[i] = static_cast<uint8_t>(value & 0xff);
                samples[i + 1] = static_cast<uint8_t>(value >> 8);
            }
        }
        else
        {
            for (auto& sample : samples)
            {
                const int centered = static_cast<int>(sample) - 128;
                sample = static_cast<uint8_t>(std::clamp(centered * volume / 100 + 128, 0, 255));
            }
        }
    }

    auto stop_voice(Voice& voice) -> void
    {
        if (voice.device)
        {
            waveOutReset(voice.device);
            if (voice.header.dwFlags & WHDR_PREPARED)
            {
                waveOutUnprepareHeader(voice.device, &voice.header, sizeof(voice.header));
            }
            waveOutClose(voice.device);
            voice.device = nullptr;
        }
    }

    auto stop_all() -> void
    {
        for (auto& voice : voices_)
        {
            stop_voice(*voice);
        }
        voices_.clear();
    }

    auto play_pcm(const PcmData& pcm, int clip, int64_t cast) -> void
    {
        auto voice = std::make_unique<Voice>();
        voice->samples = pcm.samples;
        scale_pcm(voice->samples, pcm.bits_per_sample, volume_);
        voice->clip = clip;
        voice->cast = cast;

        WAVEFORMATEX format{};
        format.wFormatTag = WAVE_FORMAT_PCM;
        format.nChannels = pcm.channels;
        format.nSamplesPerSec = pcm.sample_rate;
        format.wBitsPerSample = pcm.bits_per_sample;
        format.nBlockAlign = static_cast<WORD>(format.nChannels * format.wBitsPerSample / 8);
        format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign;

        MMRESULT result = waveOutOpen(&voice->device, WAVE_MAPPER, &format, 0, 0, CALLBACK_NULL);
        if (result != MMSYSERR_NOERROR)
        {
            throw std::runtime_error("waveOutOpen failed with code " + std::to_string(result));
        }

        voice->header.lpData = reinterpret_cast<LPSTR>(voice->samples.data());
        voice->header.dwBufferLength = static_cast<DWORD>(voice->samples.size());
        result = waveOutPrepareHeader(voice->device, &voice->header, sizeof(voice->header));
        if (result == MMSYSERR_NOERROR)
        {
            result = waveOutWrite(voice->device, &voice->header, sizeof(voice->header));
        }
        if (result != MMSYSERR_NOERROR)
        {
            stop_voice(*voice);
            throw std::runtime_error("waveOut submission failed with code " + std::to_string(result));
        }
        voices_.push_back(std::move(voice));
    }

    auto play(int clip, int64_t cast) -> void
    {
        if (!ready_ || clip < 1 || clip > 4)
        {
            return;
        }
        if (clip == 4 && cast > 0 && hit_casts_.contains(cast))
        {
            return;
        }
        if (voices_.size() >= 12)
        {
            stop_all();
        }
        play_pcm(clips_[static_cast<size_t>(clip)], clip, cast);
    }

    auto play_hit(int64_t cast) -> void
    {
        if (!ready_)
        {
            return;
        }
        hit_casts_.insert(cast);
        for (auto it = voices_.begin(); it != voices_.end();)
        {
            if ((*it)->clip == 4 && (*it)->cast == cast)
            {
                stop_voice(**it);
                it = voices_.erase(it);
            }
            else
            {
                ++it;
            }
        }
        if (voices_.size() >= 12)
        {
            stop_all();
        }
        play_pcm(clips_[5], 5, cast);
    }

public:
    auto initialize() -> void
    {
        try
        {
            const auto directory = pcm_path();
            const std::array<std::wstring, 6> names{L"charge_stage_1.wav", L"charge_stage_2.wav", L"charge_stage_3.wav",
                                                    L"ground_impact.wav", L"full_charge_hit_1.wav", L"full_charge_hit_2.wav"};
            for (size_t i = 0; i < names.size(); ++i)
            {
                clips_[i + 1] = read_pcm(directory / names[i]);
            }

            auto& hit_sequence = clips_[5];
            const auto& second_hit_clip = clips_[6];
            hit_sequence.samples.insert(hit_sequence.samples.end(), second_hit_clip.samples.begin(), second_hit_clip.samples.end());
            ready_ = true;
            write_mod_log(L"Loaded six PCM WAV clips for in-process playback");
        }
        catch (const std::exception& error)
        {
            const std::string message = std::string("Audio initialization failed: ") + error.what();
            write_mod_log(std::wstring(message.begin(), message.end()).c_str());
        }
    }

    auto dispatch(const LuaMadeSimple::Lua& lua) -> bool
    {
        if (!lua.is_string(1))
        {
            lua.set_bool(false);
            return false;
        }

        const std::string action{lua.get_string(1)};
        try
        {
            std::scoped_lock lock(mutex_);
            int clip = 0;
            int64_t cast = 0;
            int volume = 0;
            if (action == "stop" || action == "quit")
            {
                stop_all();
            }
            else if (!ready_)
            {
                lua.set_bool(false);
                return false;
            }
            else if (action == "volume" && lua.is_integer(1))
            {
                volume = static_cast<int>(lua.get_integer(1));
                volume_ = std::clamp(volume, 0, 200);
                if (volume_ == 0)
                {
                    stop_all();
                }
            }
            else if (action == "play" && lua.is_integer(1))
            {
                clip = static_cast<int>(lua.get_integer(1));
                cast = lua.is_integer(1) ? lua.get_integer(1) : 0;
                play(clip, cast);
            }
            else if (action == "hit" && lua.is_integer(1))
            {
                cast = lua.get_integer(1);
                play_hit(cast);
            }
            else
            {
                lua.set_bool(false);
                return false;
            }

            std::wstring message = L"Audio command accepted: " + std::wstring(action.begin(), action.end());
            if (action == "play")
            {
                message += L" clip=" + std::to_wstring(clip) + L" cast=" + std::to_wstring(cast);
            }
            else if (action == "hit")
            {
                message += L" cast=" + std::to_wstring(cast);
            }
            else if (action == "volume")
            {
                message += L" percent=" + std::to_wstring(volume);
            }
            write_mod_log(message.c_str());
            lua.set_bool(true);
            return true;
        }
        catch (const std::exception& error)
        {
            const std::string message = std::string("Audio command failed: ") + error.what();
            write_mod_log(std::wstring(message.begin(), message.end()).c_str());
            lua.set_bool(false);
            return false;
        }
    }

    auto update() -> void
    {
        std::scoped_lock lock(mutex_);
        for (auto it = voices_.begin(); it != voices_.end();)
        {
            if ((*it)->header.dwFlags & WHDR_DONE)
            {
                stop_voice(**it);
                it = voices_.erase(it);
            }
            else
            {
                ++it;
            }
        }
    }

    auto shutdown() -> void
    {
        std::scoped_lock lock(mutex_);
        stop_all();
        ready_ = false;
    }
};

AudioPlayer g_audio_player;

auto widen_utf8(std::string_view value) -> std::wstring
{
    const int length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
                                            static_cast<int>(value.size()), nullptr, 0);
    if (length <= 0)
    {
        throw std::runtime_error("could not decode UTF-8 path");
    }
    std::wstring result(static_cast<size_t>(length), L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()),
                        result.data(), length);
    return result;
}

auto run_hidden_powershell(const LuaMadeSimple::Lua& lua) -> int
{
    if (!lua.is_string(1) || !lua.is_string(2) || !lua.is_string(3))
    {
        lua.set_bool(false);
        return 1;
    }

    const std::string script_utf8{lua.get_string(1)};
    const std::string root_utf8{lua.get_string(1)};
    const std::string install_version{lua.get_string(1)};
    try
    {
        wchar_t system_directory[MAX_PATH]{};
        const UINT length = GetSystemDirectoryW(system_directory, MAX_PATH);
        if (length == 0 || length >= MAX_PATH)
        {
            throw std::runtime_error("could not resolve Windows system directory");
        }

        const std::wstring executable = std::filesystem::path(system_directory)
            .append(L"WindowsPowerShell").append(L"v1.0").append(L"powershell.exe").wstring();
        const std::wstring script = widen_utf8(script_utf8);
        const std::wstring mod_root = widen_utf8(root_utf8);
        const std::wstring version = widen_utf8(install_version);
        std::wstring command_line = L"\"" + executable
            + L"\" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File \""
            + script + L"\" -ModRoot \"" + mod_root + L"\" -InstallVersion \"" + version + L"\"";

        STARTUPINFOW startup{};
        startup.cb = sizeof(startup);
        startup.dwFlags = STARTF_USESHOWWINDOW;
        startup.wShowWindow = SW_HIDE;
        PROCESS_INFORMATION process{};
        if (!CreateProcessW(executable.c_str(), command_line.data(), nullptr, nullptr, FALSE,
                            CREATE_NO_WINDOW, nullptr, nullptr, &startup, &process))
        {
            throw std::runtime_error("could not start hidden menu installer");
        }

        const DWORD wait_result = WaitForSingleObject(process.hProcess, 30000);
        DWORD exit_code = 1;
        if (wait_result == WAIT_OBJECT_0)
        {
            GetExitCodeProcess(process.hProcess, &exit_code);
        }
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        lua.set_bool(wait_result == WAIT_OBJECT_0 && exit_code == 0);
        return 1;
    }
    catch (const std::exception& error)
    {
        const std::string message = std::string("Menu installer failed: ") + error.what();
        write_mod_log(std::wstring(message.begin(), message.end()).c_str());
        lua.set_bool(false);
        return 1;
    }
}

auto audio_command(const LuaMadeSimple::Lua& lua) -> int
{
    g_audio_player.dispatch(lua);
    return 1;
}

class PBZChiRenNativeAudio final : public CppUserModBase
{
public:
    PBZChiRenNativeAudio()
    {
        ModName = L"PBZChiRenNativeAudio";
        ModVersion = L"1.1";
        ModAuthors = L"PBZChiRenDarkSword";
        ModDescription = L"In-process WAV audio playback";
    }

    auto on_unreal_init() -> void override
    {
        g_audio_player.initialize();
    }

    auto on_lua_start(StringViewType mod_name, LuaMadeSimple::Lua& lua, LuaMadeSimple::Lua&, LuaMadeSimple::Lua&,
                      LuaMadeSimple::Lua*) -> void override
    {
        if (mod_name == L"PBZChiRenDarkSword")
        {
            lua.register_function("PBZ_PlayAudio", audio_command);
            lua.register_function("PBZ_RunHiddenPowerShell", run_hidden_powershell);
            write_mod_log(L"Registered PBZ_PlayAudio with PBZChiRenDarkSword Lua mod");
        }
    }

    auto on_update() -> void override
    {
        g_audio_player.update();
    }

    ~PBZChiRenNativeAudio() override
    {
        g_audio_player.shutdown();
    }
};
}

#define MOD_EXPORT __declspec(dllexport)
extern "C"
{
MOD_EXPORT RC::CppUserModBase* start_mod()
{
    return new RC::PBZChiRenNativeAudio();
}

MOD_EXPORT void uninstall_mod(RC::CppUserModBase* mod)
{
    delete mod;
}
}
