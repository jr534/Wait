#include <QCoreApplication>
#include <QHostAddress>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStringList>
#include <QTimer>
#include <QWebSocket>
#include <QWebSocketServer>

namespace {

QByteArray makeMessage(const QString &type, const QJsonObject &payload = {})
{
    QJsonObject message;
    message["type"] = type;
    if (!payload.isEmpty()) {
        message["payload"] = payload;
    }
    return QJsonDocument(message).toJson(QJsonDocument::Compact);
}

QString placeholderSvgBase64(const QString &label)
{
    const QString svg = QStringLiteral(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"96\" height=\"96\" viewBox=\"0 0 96 96\">"
        "<rect width=\"96\" height=\"96\" rx=\"18\" fill=\"#111827\"/>"
        "<circle cx=\"48\" cy=\"38\" r=\"16\" fill=\"#38bdf8\"/>"
        "<text x=\"48\" y=\"70\" font-size=\"12\" fill=\"#ffffff\" text-anchor=\"middle\" font-family=\"Arial\">%1</text>"
        "</svg>")
        .arg(label.toHtmlEscaped());

    return QString::fromUtf8(svg.toUtf8().toBase64());
}

void streamDemoResponse(QWebSocket *client)
{
    const QStringList parts = {
        "WAIT analyse la demande, ",
        "selectionne des icones semantiques, ",
        "puis affiche la reponse du LLM en streaming."
    };

    for (int i = 0; i < parts.size(); ++i) {
        QTimer::singleShot(1200 + i * 700, client, [client, part = parts[i]] {
            if (client->state() != QAbstractSocket::ConnectedState) {
                return;
            }
            client->sendTextMessage(makeMessage("LLM/rep", {{"reponse_part", part}}));
        });
    }
}

} // namespace

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    QWebSocketServer server(QStringLiteral("WAIT backend"), QWebSocketServer::NonSecureMode);
    const quint16 port = 8765;

    if (!server.listen(QHostAddress::Any, port)) {
        qCritical("Unable to start WAIT WebSocket server");
        return 1;
    }

    qInfo("WAIT backend listening on ws://localhost:%u", port);

    QObject::connect(&server, &QWebSocketServer::newConnection, [&server] {
        QWebSocket *client = server.nextPendingConnection();

        QObject::connect(client, &QWebSocket::textMessageReceived, client, [client](const QString &rawMessage) {
            const QJsonDocument document = QJsonDocument::fromJson(rawMessage.toUtf8());
            const QJsonObject message = document.object();

            if (message["type"].toString() != "user/ask") {
                return;
            }

            client->sendTextMessage(makeMessage("user/ask/ack"));
            client->sendTextMessage(makeMessage("wait", {
                {"t_icon1", 1.5},
                {"name_icon1", "analyse"},
                {"icon1", placeholderSvgBase64("analyse")},
                {"t_icon2", 5.0},
                {"name_icon2", "recherche"},
                {"icon2", placeholderSvgBase64("search")},
                {"t_icon3", 7.5},
                {"name_icon3", "synthese"},
                {"icon3", placeholderSvgBase64("reply")}
            }));

            streamDemoResponse(client);
        });

        QObject::connect(client, &QWebSocket::disconnected, client, &QObject::deleteLater);
    });

    return app.exec();
}
