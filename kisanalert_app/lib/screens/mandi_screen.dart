// lib/screens/mandi_screen.dart
// ⭐ MANDI MAP — Real Google Maps SDK integration for Marathwada APMC mandis
// Shows live price markers, tappable pins, and signal colour coding on satellite map.

import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:geolocator/geolocator.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../data/app_data.dart';
import '../widgets/shared_widgets.dart';

// ── Mandi GPS Coordinates (Marathwada, Maharashtra) ──────────────────────────
const _mandiCoords = {
  'Nanded':    LatLng(19.1527, 77.3218),
  'Latur':     LatLng(18.3956, 76.5604),
  'Osmanabad': LatLng(18.1859, 76.0435),
  'Hingoli':   LatLng(19.7186, 77.1493),
  'Parbhani':  LatLng(19.2718, 76.7747),
  'Nandurbar': LatLng(21.3653, 74.2441),
  'Biloli':    LatLng(18.7667, 77.7500),
  'Mudkhed':   LatLng(18.6833, 77.6667),
};

// Marathwada geographic centre
const _marathwadaCenter = LatLng(18.75, 76.70);

class MandiScreen extends StatefulWidget {
  final AppState state;
  final Function(MandiData) onOpenMandi;

  const MandiScreen({super.key, required this.state, required this.onOpenMandi});

  @override
  State<MandiScreen> createState() => _MandiScreenState();
}

class _MandiScreenState extends State<MandiScreen> {
  GoogleMapController? _mapCtrl;
  bool _mapReady = false;
  bool _mapError = false;
  Set<Marker> _markers = {};
  bool _locationGranted = false;
  Position? _userPosition;

  @override
  void initState() {
    super.initState();
    _buildMarkers();
    _requestLocationPermission();
  }

  @override
  void didUpdateWidget(MandiScreen old) {
    super.didUpdateWidget(old);
    if (old.state.activeCrop != widget.state.activeCrop ||
        old.state.currentMandis.length != widget.state.currentMandis.length) {
      _buildMarkers();
    }
  }

  Future<void> _requestLocationPermission() async {
    try {
      final status = await Permission.location.request();
      if (status.isGranted) {
        if (mounted) setState(() => _locationGranted = true);
        _fetchAndCenterUserLocation();
      } else if (status.isDenied && mounted) {
        // Show farmer-friendly dialog
        _showLocationDialog();
      }
    } catch (_) {}
  }

  Future<void> _fetchAndCenterUserLocation() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      if (mounted) {
        setState(() => _userPosition = pos);
        _mapCtrl?.animateCamera(CameraUpdate.newLatLngZoom(
          LatLng(pos.latitude, pos.longitude), 10.0,
        ));
      }
    } catch (_) {}
  }

  void _showLocationDialog() {
    if (!mounted) return;
    final isMarathi = widget.state.isMarathi;
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(isMarathi ? '📍 तुमचे स्थान' : '📍 Your Location',
            style: GoogleFonts.spaceGrotesk(fontWeight: FontWeight.w700)),
        content: Text(
          isMarathi
              ? 'जवळची मंडी दाखवण्यासाठी आम्हाला तुमच्या स्थानाची परवानगी द्या.'
              : 'Allow location access to show your nearest mandi on the map.',
          style: GoogleFonts.workSans(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(isMarathi ? 'नंतर' : 'Later'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.green),
            onPressed: () {
              Navigator.pop(context);
              openAppSettings();
            },
            child: Text(isMarathi ? 'परवानगी द्या' : 'Allow',
                style: const TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _buildMarkers() {
    final mandis = widget.state.currentMandis;
    final crop   = widget.state.activeCrop;

    final Set<Marker> markers = {};
    for (final mandi in mandis) {
      final coords = _mandiCoords[mandi.name];
      if (coords == null) continue;

      final price = mandi.priceForCrop(crop);
      final signal = mandi.signal;
      final hue = _signalHue(signal);

      markers.add(Marker(
        markerId: MarkerId(mandi.name),
        position: coords,
        icon: BitmapDescriptor.defaultMarkerWithHue(hue),
        infoWindow: InfoWindow(
          title: '${_signalEmoji(signal)} ${mandi.name}',
          snippet: '₹${price.toStringAsFixed(0)}/qtl · ${mandi.distanceKm}km · $signal',
          onTap: () => widget.onOpenMandi(mandi),
        ),
        onTap: () {
          _mapCtrl?.showMarkerInfoWindow(MarkerId(mandi.name));
        },
      ));
    }

    // Also add static mandis not yet in live data
    for (final entry in _mandiCoords.entries) {
      if (markers.any((m) => m.markerId.value == entry.key)) continue;
      markers.add(Marker(
        markerId: MarkerId(entry.key),
        position: entry.value,
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueOrange),
        infoWindow: InfoWindow(
          title: '📍 ${entry.key} APMC',
          snippet: 'Data loading...',
        ),
      ));
    }

    if (mounted) setState(() => _markers = markers);
  }

  double _signalHue(String signal) {
    switch (signal) {
      case 'RED':   return BitmapDescriptor.hueRed;
      case 'GREEN': return BitmapDescriptor.hueGreen;
      case 'BLUE':  return BitmapDescriptor.hueAzure;
      default:      return BitmapDescriptor.hueYellow;
    }
  }

  String _signalEmoji(String signal) {
    switch (signal) {
      case 'RED':   return '🚨';
      case 'GREEN': return '✅';
      case 'BLUE':  return '💎';
      default:      return '⚠️';
    }
  }

  void _findNearestMandi() {
    if (_userPosition == null) {
      _requestLocationPermission();
      return;
    }
    // Find nearest mandi by GPS distance
    MandiData? nearest;
    double nearestDist = double.infinity;
    for (final mandi in widget.state.currentMandis) {
      final coords = _mandiCoords[mandi.name];
      if (coords == null) continue;
      final d = Geolocator.distanceBetween(
        _userPosition!.latitude, _userPosition!.longitude,
        coords.latitude, coords.longitude,
      );
      if (d < nearestDist) { nearestDist = d; nearest = mandi; }
    }
    if (nearest != null) {
      final coords = _mandiCoords[nearest.name]!;
      _mapCtrl?.animateCamera(CameraUpdate.newLatLngZoom(coords, 12.0));
      _mapCtrl?.showMarkerInfoWindow(MarkerId(nearest.name));
    }
  }

  @override
  void dispose() {
    _mapCtrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    // ── 1. Map Widget ──
    Widget mapWidget = SizedBox(
      height: 320,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        child: _GoogleMandiMap(
          isDark: isDark,
          markers: _markers,
          isReady: _mapReady,
          isError: _mapError,
          locationGranted: _locationGranted,
          onMapCreated: (ctrl) {
            _mapCtrl = ctrl;
            setState(() => _mapReady = true);
            if (_userPosition != null) {
              ctrl.animateCamera(CameraUpdate.newLatLngZoom(
                LatLng(_userPosition!.latitude, _userPosition!.longitude), 10.0));
            }
          },
          onError: () => setState(() { _mapError = true; _mapReady = false; }),
          onFindNearestMandi: _findNearestMandi,
        ),
      ),
    );

    // ── 2. Scrollable List Content ──
    Widget listContentWidget = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 10),

        // Map legend
        _MapLegend(isDark: isDark, isMarathi: widget.state.isMarathi),
        const SizedBox(height: 16),

        // Crop filter
        _CropFilter(state: widget.state, isDark: isDark),
        const SizedBox(height: 20),

        // Ranked mandi list
        Text(
          widget.state.isMarathi ? 'आजचे सर्वोत्तम मंडी' : 'Best Mandis Today',
          style: GoogleFonts.spaceGrotesk(
              fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary),
        ),
        Text(
          widget.state.isMarathi ? 'नफ्यानुसार क्रम' : 'Ranked by net profit after transport cost',
          style: GoogleFonts.workSans(fontSize: 12, color: textMuted),
        ),
        const SizedBox(height: 12),

        ...() {
          final sorted = [...widget.state.currentMandis]
            ..sort((a, b) => b.priceForCrop(widget.state.activeCrop)
                .compareTo(a.priceForCrop(widget.state.activeCrop)));
          final ranks = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣'];
          return sorted.asMap().entries.map((e) => MandiCard(
            rank: ranks[e.key < ranks.length ? e.key : ranks.length - 1],
            name: e.value.name,
            distanceKm: e.value.distanceKm,
            price: e.value.priceForCrop(widget.state.activeCrop),
            signal: e.value.signal,
            weather: e.value.weather,
            advice: e.value.advice,
            isDark: isDark,
            activeCrop: widget.state.activeCrop,
            isBest: e.value.isBest,
            onTap: () {
              widget.onOpenMandi(e.value);
              final coords = _mandiCoords[e.value.name];
              if (coords != null && _mapCtrl != null) {
                _mapCtrl!.animateCamera(
                  CameraUpdate.newLatLngZoom(coords, 12.0),
                );
                _mapCtrl!.showMarkerInfoWindow(MarkerId(e.value.name));
              }
            },
          ));
        }(),
        const SizedBox(height: 20),

        // Lead-Lag Engine card
        _LeadLagCard(isDark: isDark, isMarathi: widget.state.isMarathi),
        const SizedBox(height: 20),

        // MSP Protection card
        _MSPCard(isDark: isDark, isMarathi: widget.state.isMarathi),
      ],
    );

    // ── 3. Platform Specific Layout ──
    if (kIsWeb) {
      // WEB: Map scrolls together with the page
      return SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        child: Column(
          children: [
            mapWidget,
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
              child: listContentWidget,
            ),
          ],
        ),
      );
    } else {
      // MOBILE: Map is sticky at the top, list scrolls underneath
      return Column(
        children: [
          NotificationListener<ScrollNotification>(
            onNotification: (_) => true,
            child: mapWidget,
          ),
          Expanded(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
              child: listContentWidget,
            ),
          ),
        ],
      );
    }
  }
}


// ── Google Maps widget ─────────────────────────────────────────────────────────
class _GoogleMandiMap extends StatelessWidget {
  final bool isDark;
  final Set<Marker> markers;
  final bool isReady;
  final bool isError;
  final bool locationGranted;
  final Function(GoogleMapController) onMapCreated;
  final VoidCallback onError;
  final VoidCallback onFindNearestMandi;

  const _GoogleMandiMap({
    required this.isDark,
    required this.markers,
    required this.isReady,
    required this.isError,
    required this.locationGranted,
    required this.onMapCreated,
    required this.onError,
    required this.onFindNearestMandi,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 320,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.15),
              blurRadius: 16, offset: const Offset(0, 6)),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          children: [
            if (!isError)
              GoogleMap(
                    onMapCreated: onMapCreated,
                    initialCameraPosition: const CameraPosition(
                      target: _marathwadaCenter,
                      zoom: 8.2,
                    ),
                    style: isDark ? _darkMapStyle : null,
                    markers: markers,
                    mapType: MapType.normal,
                    myLocationEnabled: locationGranted,        // blue dot when allowed
                    myLocationButtonEnabled: locationGranted,  // top-right GPS button
                    zoomControlsEnabled: false,
                    compassEnabled: true,
                    mapToolbarEnabled: false,
                    gestureRecognizers: {
                      Factory<OneSequenceGestureRecognizer>(() => EagerGestureRecognizer()),
                    },
                  )
            else
              _MapErrorFallback(isDark: isDark),

            // Loading overlay
            if (!isReady && !isError)
              Container(
                color: (isDark ? const Color(0xFF1A1A12) : const Color(0xFFF9F4E8))
                    .withValues(alpha: 0.85),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const CircularProgressIndicator(color: AppColors.green),
                      const SizedBox(height: 12),
                      Text('Loading Mandi Map...',
                          style: GoogleFonts.workSans(
                              color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
                    ],
                  ),
                ),
              ),

            // Top overlay — "Google Maps Powered" badge
            Positioned(
              top: 12, left: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(999),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.1), blurRadius: 8)],
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Text('📍', style: TextStyle(fontSize: 12)),
                  const SizedBox(width: 4),
                  Text('Marathwada APMC Mandis',
                      style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w700,
                          color: const Color(0xFF1A1A1A))),
                ]),
              ),
            ),

            // "Find Nearest Mandi" FAB — bottom right
            Positioned(
              right: 12, bottom: 12,
              child: GestureDetector(
                onTap: onFindNearestMandi,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppColors.green,
                    borderRadius: BorderRadius.circular(999),
                    boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 8)],
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.near_me_rounded, color: Colors.white, size: 16),
                    const SizedBox(width: 6),
                    Text('Nearest Mandi',
                        style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w700,
                            color: Colors.white)),
                  ]),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}




// ── Map Error Fallback ─────────────────────────────────────────────────────────
class _MapErrorFallback extends StatelessWidget {
  final bool isDark;
  const _MapErrorFallback({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: isDark ? const Color(0xFF1A1A12) : const Color(0xFFF9F4E8),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('🗺️', style: TextStyle(fontSize: 40)),
            const SizedBox(height: 10),
            Text('Add Maps API Key in AndroidManifest.xml',
                style: GoogleFonts.workSans(
                    color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary,
                    fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Text('Google Cloud Console → Maps SDK for Android',
                style: GoogleFonts.workSans(fontSize: 11,
                    color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
          ],
        ),
      ),
    );
  }
}


// ── Map Legend ─────────────────────────────────────────────────────────────────
class _MapLegend extends StatelessWidget {
  final bool isDark;
  final bool isMarathi;
  const _MapLegend({required this.isDark, required this.isMarathi});

  @override
  Widget build(BuildContext context) {
    final items = [
      (AppColors.red,   '🚨', isMarathi ? 'आजच विक्री करा' : 'Sell Now'),
      (AppColors.green, '✅', isMarathi ? 'आजच विका' : 'Sell Now'),
      (const Color(0xFF1D4ED8), '💎', isMarathi ? 'थांबा' : 'Hold'),
      (AppColors.amber, '⚠️', isMarathi ? 'तुमची निवड' : 'Neutral'),
    ];
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: items.map((item) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 10, height: 10,
              decoration: BoxDecoration(color: item.$1, shape: BoxShape.circle)),
          const SizedBox(width: 4),
          Text(item.$3, style: GoogleFonts.workSans(fontSize: 10,
              color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
        ]),
      )).toList(),
    );
  }
}


// ── Crop Filter ────────────────────────────────────────────────────────────────
class _CropFilter extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _CropFilter({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final crops = [
      ('Soybean', '🌱', 'सोयाबीन'),
      ('Cotton', '🌿', 'कापूस'),
      ('Turmeric', '🌾', 'हळद'),
    ];
    return Row(
      children: crops.map((c) {
        final isActive = state.activeCrop == c.$1;
        return Expanded(
          child: GestureDetector(
            onTap: () => state.setActiveCrop(c.$1),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: isActive ? AppColors.green : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                    color: isActive ? AppColors.green : AppColors.green.withValues(alpha: 0.3)),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(c.$2, style: const TextStyle(fontSize: 18)),
                  Text(state.isMarathi ? c.$3 : c.$1,
                      style: GoogleFonts.workSans(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: isActive ? Colors.white
                              : (isDark ? AppColors.darkTextPrimary : AppColors.textPrimary))),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}


// ── Lead-Lag Engine Card ───────────────────────────────────────────────────────
class _LeadLagCard extends StatelessWidget {
  final bool isDark;
  final bool isMarathi;
  const _LeadLagCard({required this.isDark, required this.isMarathi});

  @override
  Widget build(BuildContext context) {
    return AgronomistCard(
      isDark: isDark,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('📡 Lead-Lag Engine Active',
              style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700,
                  color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
          const SizedBox(height: 12),
          Row(children: [
            _LagBox(label: 'Latur', sub: isMarathi ? '४८ तास आधी' : '48h ahead', color: AppColors.blue, isDark: isDark),
            _Arrow(isDark: isDark),
            _LagBox(label: 'Nanded', sub: isMarathi ? 'आजचे मूल्य' : 'Today\'s price', color: AppColors.green, isDark: isDark),
            _Arrow(isDark: isDark),
            _LagBox(label: 'Osmanabad', sub: isMarathi ? '२४ तास मागे' : '24h behind', color: AppColors.amber, isDark: isDark),
          ]),
          const SizedBox(height: 10),
          Text(
            isMarathi
                ? 'लातूरचे भाव नांदेडच्या ४८ तास आधी हलतात — आमचे AI हे पॅटर्न वापरते'
                : 'Latur prices move 48h before Nanded — our AI uses this pattern',
            style: GoogleFonts.workSans(fontSize: 12,
                color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _LagBox extends StatelessWidget {
  final String label, sub;
  final Color color;
  final bool isDark;
  const _LagBox({required this.label, required this.sub, required this.color, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(children: [
          Text(label, style: GoogleFonts.spaceGrotesk(
              fontSize: 12, fontWeight: FontWeight.w700, color: color)),
          Text(sub, textAlign: TextAlign.center,
              style: GoogleFonts.workSans(fontSize: 9,
                  color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
        ]),
      ),
    );
  }
}

class _Arrow extends StatelessWidget {
  final bool isDark;
  const _Arrow({required this.isDark});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4),
    child: Icon(Icons.arrow_forward_ios_rounded, size: 14,
        color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
  );
}


// ── MSP Protection Card ───────────────────────────────────────────────────────
class _MSPCard extends StatelessWidget {
  final bool isDark;
  final bool isMarathi;
  const _MSPCard({required this.isDark, required this.isMarathi});

  @override
  Widget build(BuildContext context) {
    return AgronomistCard(
      isDark: isDark,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(isMarathi ? '🛡️ MSP संरक्षण' : '🛡️ MSP Protection',
              style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700,
                  color: AppColors.blueText)),
          const SizedBox(height: 6),
          Text(isMarathi ? 'सरकारला MSP वर खरेदी करणे बंधनकारक आहे'
              : 'Government must buy at MSP',
              style: GoogleFonts.workSans(fontSize: 12, color: AppColors.blueText)),
          const SizedBox(height: 10),
          ...['NAFED Nanded · 📞 02462-281234',
              'APMC Biloli · 📞 02461-222345',
              'NAFED Hingoli · 📞 02456-234123']
              .map((c) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Text(c, style: GoogleFonts.workSans(
                        fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.blueText)),
                  )),
        ],
      ),
    );
  }
}

// ── Web Map Placeholder (shown on Chrome/Web since Maps API key is not web-authorized) ──
class _WebMapPlaceholder extends StatelessWidget {
  final bool isDark;
  const _WebMapPlaceholder({required this.isDark});

  @override
  Widget build(BuildContext context) {
    final bg = isDark ? const Color(0xFF1A2A1A) : const Color(0xFFE8F5E9);
    final textColor = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final mutedColor = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    return Container(
      color: bg,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.map_outlined, size: 64, color: AppColors.green.withValues(alpha: 0.6)),
            const SizedBox(height: 16),
            Text('मराठवाडा APMC मंडी नकाशा',
                style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textColor)),
            const SizedBox(height: 6),
            Text('Nanded · Latur · Hingoli · Parbhani · Osmanabad',
                style: GoogleFonts.workSans(fontSize: 12, color: mutedColor),
                textAlign: TextAlign.center),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.greenPale,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text('📱 Full map available on mobile app',
                  style: GoogleFonts.workSans(fontSize: 12, color: AppColors.greenText, fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }
}


// ── Dark Mode Map Style (Google Maps JSON) ────────────────────────────────────
const _darkMapStyle = '''[
  {"elementType":"geometry","stylers":[{"color":"#1d2c4d"}]},
  {"elementType":"labels.text.fill","stylers":[{"color":"#8ec3b9"}]},
  {"elementType":"labels.text.stroke","stylers":[{"color":"#1a3646"}]},
  {"featureType":"administrative.country","elementType":"geometry.stroke","stylers":[{"color":"#4b6878"}]},
  {"featureType":"landscape.natural","elementType":"geometry","stylers":[{"color":"#023e58"}]},
  {"featureType":"poi","elementType":"geometry","stylers":[{"color":"#283d6a"}]},
  {"featureType":"road","elementType":"geometry","stylers":[{"color":"#304a7d"}]},
  {"featureType":"road","elementType":"labels.text.fill","stylers":[{"color":"#98a5be"}]},
  {"featureType":"water","elementType":"geometry","stylers":[{"color":"#0e1626"}]},
  {"featureType":"water","elementType":"labels.text.fill","stylers":[{"color":"#4e6d70"}]}
]''';
